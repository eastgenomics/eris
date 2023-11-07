import datetime as dt
import pandas as pd
import re
import numpy as np
from django.db import transaction

pd.options.mode.chained_assignment = None  # default='warn'
import datetime

from .history import History
from requests_app.models import (
    Gene,
    Transcript,
    TranscriptRelease,
    TranscriptSource,
    TranscriptFile,
    TranscriptReleaseTranscript,
    TranscriptReleaseTranscriptFile,
    PanelGene,
    HgncRelease,
    GeneHgncRelease,
    GeneHgncReleaseHistory,
    ReferenceGenome,
)


def _update_existing_gene_metadata_symbol_in_db(
    hgnc_id_to_approved_symbol: dict[str:str],
    hgnc_release: HgncRelease,
    user: str
) -> None:
    """
    Function to update gene metadata in db using hgnc dump prepared dictionaries
    Updates approved symbol if that has changed.
    To speed up the function, we utilise looping over lists-of-dictionaries,
    and bulk updates in some spots.

    :param hgnc_id_to_approved_symbol: dictionary of hgnc id to approved symbol
    :param hgnc_release: the HgncRelease for the currently-uploaded HGNC file
    :param user: currently a string to describe the user
    """

    every_db_gene = [{i.hgnc_id: i.gene_symbol} for i in Gene.objects.all()]

    gene_symbol_updates = []

    # queue up genes which need updating because their approved symbols have
    # changed in HGNC
    for gene_info in every_db_gene:
        for hgnc_id, gene_symbol in gene_info.items():
            # if gene symbol in db differ from approved symbol in hgnc
            if hgnc_id in hgnc_id_to_approved_symbol:
                if gene_symbol != hgnc_id_to_approved_symbol[hgnc_id]:
                    # queue up the Gene object to be updated
                    gene = Gene.objects.get(hgnc_id=hgnc_id)
                    gene.gene_symbol = hgnc_id_to_approved_symbol[hgnc_id]
                    gene_symbol_updates.append(gene)

    # bulk update the changed genes
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"Start gene symbol bulk update: {now}")
    Gene.objects.bulk_update(gene_symbol_updates, ["gene_symbol"])

    # for each changed gene, link to release and add a note
    for gene in gene_symbol_updates:
        gene_hgnc_release = GeneHgncRelease.objects.create(
            gene=gene,
            hgnc_release=hgnc_release
        )

        GeneHgncReleaseHistory(gene_hgnc_release=gene_hgnc_release,
                           note=History.gene_hgnc_release_approved_symbol_change,
                           user=user)


def _update_existing_gene_metadata_aliases_in_db(
    hgnc_id_to_alias_symbols: dict[str:str],
    hgnc_release: HgncRelease,
    user: str
) -> None:
    """
    Function to update gene metadata in db using hgnc dump prepared dictionaries
    Updates alias symbols if those have changed.
    To speed up the function, we utilise looping over lists-of-dictionaries,
    and bulk updates.

    :param hgnc_id_to_alias_symbols: dictionary of hgnc id to alias symbols
    :param hgnc_release: the HgncRelease for the currently-uploaded HGNC file
    :param user: currently a string to describe the user
    """

    hgnc_id_list = [{i.hgnc_id: i.alias_symbols} for i in Gene.objects.all()]

    gene_alias_updates = []

    for gene_info in hgnc_id_list:
        for hgnc_id, alias_symbols in gene_info.items():
            # if hgnc id in dictionary, and alias symbols are not all pd.nan
            if (
                hgnc_id in hgnc_id_to_alias_symbols
                and not pd.isna(hgnc_id_to_alias_symbols[hgnc_id]).all()
            ):
                joined_new_alias_symbols = ",".join(hgnc_id_to_alias_symbols[hgnc_id])
                if alias_symbols != joined_new_alias_symbols:
                    gene = Gene.objects.get(hgnc_id=hgnc_id)
                    gene.alias_symbols = joined_new_alias_symbols
                    gene_alias_updates.append(gene)

    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"Start gene alias bulk update: {now}")
    Gene.objects.bulk_update(gene_alias_updates, ["alias_symbols"])

    # for each changed gene, link to release and add a note
    for gene in gene_alias_updates:
        gene_hgnc_release = GeneHgncRelease.objects.create(
            gene=gene,
            hgnc_release=hgnc_release
        )

        GeneHgncReleaseHistory(gene_hgnc_release=gene_hgnc_release,
                           note=History.gene_hgnc_release_alias_symbol_change,
                           user=user)


def _add_new_genes_to_db(
    approved_symbols: dict[str:str], alias_symbols: dict[str:list],
    hgnc_release: HgncRelease, user: str
) -> None:
    """
    If a gene exists in the HGNC file, but does NOT exist in the db, make it.
    Link the gene to the HGNC file's release, to help with auditing.
    To speed up the function, we utilise looping over lists-of-dictionaries,
    and bulk updates in some places.

    :param approved_symbols: dictionary of hgnc id to approved symbols
    :param alias_symbols: dictionary of hgnc id to alias symbols
    :param hgnc_release: the HgncRelease for the currently-uploaded HGNC file
    :param user: currently a string to describe the user
    """
    genes_to_create = []

    # all hgncs already in db
    already_exist = [i.hgnc_id for i in Gene.objects.all()]

    # get all possible HGNC IDs
    all_hgnc_in_approved = list(set(approved_symbols.keys()))
    all_hgnc_in_alias = list(set(alias_symbols.keys()))
    hgncs = all_hgnc_in_alias + all_hgnc_in_approved
    hgncs_not_in_db = list(set(hgncs) - set(already_exist))

    for hgnc_id in hgncs_not_in_db:
        # get approved symbols
        matches = approved_symbols[hgnc_id]
        if matches:
            symbol_match = matches
        else:
            symbol_match = None

        # get aliases
        matches = alias_symbols[hgnc_id]
        if matches:
            alias_match = matches
        else:
            alias_match = None

        new_gene = Gene(
            hgnc_id=hgnc_id, gene_symbol=symbol_match, alias_symbols=alias_match
        )
        genes_to_create.append(new_gene)

    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"Start gene bulk create: {now}")
    new_genes = Gene.objects.bulk_create(genes_to_create)

    # for each new gene, link to release and add a note
    for gene in new_genes:
        gene_hgnc_release = GeneHgncRelease.objects.create(
            gene=gene,
            hgnc_release=hgnc_release
        )

        GeneHgncReleaseHistory(gene_hgnc_release=gene_hgnc_release,
                           note=History.gene_hgnc_release_new,
                           user=user)


def _prepare_hgnc_file(hgnc_file: str, hgnc_version: str, user: str) -> dict[str, str]:
    """
    Read hgnc file, sanity-check it, and prepare four dictionaries:
    1. gene symbol to hgnc id
    2. hgnc id to approved symbol
    4. hgnc id to alias symbols

    Create a HGNC release version if applicable

    Finally, update any metadata for existing genes in the Eris database -
    if this has changed since the last HGNC upload.

    :param hgnc_file: hgnc file path
    :param hgnc_version: a string describing the in-house-assigned release version of 
    the HGNC file
    :param user: str, the user's name
    :return: gene symbol to hgnc id dict
    """
    hgnc: pd.DataFrame = pd.read_csv(hgnc_file, delimiter="\t")

    needed_cols = ["HGNC ID", "Approved symbol", "Alias symbols"]
    _sanity_check_cols_exist(hgnc, needed_cols, "HGNC dump")

    # prepare dictionary files
    hgnc_symbol_to_hgnc_id = dict(zip(hgnc["Approved symbol"], hgnc["HGNC ID"]))

    hgnc_id_to_approved_symbol = dict(zip(hgnc["HGNC ID"], hgnc["Approved symbol"]))
    hgnc_id_to_alias_symbols = (
        hgnc.groupby("HGNC ID")["Alias symbols"].apply(list).to_dict()
    )

    # create HGNC release
    hgnc_release, _ = HgncRelease.objects.create(hgnc_release=hgnc_version)

    with transaction.atomic():
        _update_existing_gene_metadata_symbol_in_db(hgnc_id_to_approved_symbol, hgnc_release,
                                                    user)
        _update_existing_gene_metadata_aliases_in_db(hgnc_id_to_alias_symbols, hgnc_release,
                                                     user)
        _add_new_genes_to_db(hgnc_id_to_approved_symbol, hgnc_id_to_alias_symbols, hgnc_release,
                             user)

    return hgnc_symbol_to_hgnc_id


def _sanity_check_cols_exist(
    df: pd.DataFrame, needed_cols: list, filename: str
) -> None:
    """
    Check for expected columns in a DataFrame.
    Collects together errors and asserts them all at once, if there's more than one issue.
    :param: df - a Pandas Dataframe
    :param: needed_cols - a list of column names to check for
    :param: filename - a reference to use for the file being checked
    :return: None
    """
    errors = []
    for x_col in needed_cols:
        if not x_col in df.columns:
            errors.append(
                f"Missing column {x_col} from {filename} file - please check the file"
            )

    errors = "; ".join(errors)
    assert not errors, errors


def _prepare_mane_file(
    mane_file: str, hgnc_symbol_to_hgnc_id: dict[str, str]
) -> list[dict]:
    """
    Read through MANE files and prepare a list of dicts,
    each dict containing a transcript, HGNC ID, and the MANE type.

    :param mane_file: mane file path
    :param hgnc_symbol_to_hgnc_id: dictionary of hgnc symbol to hgnc id
        to turn gene-id in mane to hgnc-id

    :return: list of dictionaries - each dict is a filtered row from the dataframe
    """
    mane = pd.read_csv(mane_file)

    needed_mane_cols = ["Gene", "MANE TYPE", "RefSeq StableID GRCh38 / GRCh37"]
    _sanity_check_cols_exist(mane, needed_mane_cols, "MANE")

    filtered_mane = mane[
        mane["MANE TYPE"].isin(["MANE SELECT", "MANE PLUS CLINICAL"])
    ]  # only mane select and mane plus clinical transcripts

    filtered_mane["HGNC ID"] = (
        filtered_mane["Gene"].astype(str).map(hgnc_symbol_to_hgnc_id)
    )

    # some renaming
    filtered_mane = filtered_mane.rename(
        columns={"RefSeq StableID GRCh38 / GRCh37": "RefSeq"}
    )
    min_cols = filtered_mane[["HGNC ID", "RefSeq", "MANE TYPE"]]

    result_dict = min_cols.to_dict("records")

    return result_dict


def _prepare_gff_file(gff_file: str) -> dict[str, list]:
    """
    Read through gff files (from DNANexus)
    and prepare dict of hgnc id to list of transcripts

    :param gff_file: gff file path

    :return: dictionary of hgnc id to list of transcripts
    """

    gff = pd.read_csv(
        gff_file,
        delimiter="\t",
        names=[
            "chrome",
            "start",
            "end",
            "hgnc",
            "transcript",
            "exon",
        ],
        dtype=str,
    )

    needed_cols = ["hgnc", "transcript"]
    _sanity_check_cols_exist(gff, needed_cols, "gff")

    return (
        gff.groupby("hgnc")
        .agg({"transcript": lambda x: list(set(list(x)))})
        .to_dict()["transcript"]
    )


def _prepare_gene2refseq_file(g2refseq_file: str) -> dict:
    """
    Reads through gene2refseq file (from HGMD database)
    and generates a dict mapping of HGMD ID to a list which can contain [refcore, refversion],
    e.g. 'id': [["NM_100", "2"]]

    :param g2refseq_file: gene2refseq file path

    :return: dictionary of hgmd id to list of not "tuple" [refcore, refversion]
    """

    # read with dtype str to avoid pandas converting to int64
    df = pd.read_csv(g2refseq_file, dtype=str)

    needed_cols = ["refcore", "refversion", "hgmdID"]
    _sanity_check_cols_exist(df, needed_cols, "gene2refseq")

    # create list of refcore + refversion
    df["core_plus_version"] = pd.Series(zip(df["refcore"], df["refversion"])).map(list)

    # make sure there's no whitespace in hgmd id
    df["hgmdId"] = df["hgmdID"].str.strip()

    # return dictionary of hgmd id to list of [refcore, refversion]
    return df.groupby("hgmdID")["core_plus_version"].apply(list).to_dict()


def _prepare_markname_file(markname_file: str) -> dict[str:list]:
    """
    Reads through markname file (from HGMD database)
    and generates a dict mapping of hgnc id to list of gene id

    :param markname_file: markname file path

    :return: dictionary of hgnc id to list of gene-id
    """
    markname = pd.read_csv(markname_file)

    needed_cols = ["hgncID"]
    _sanity_check_cols_exist(markname, needed_cols, "markname")

    return markname.groupby("hgncID")["gene_id"].apply(list).to_dict()


def _add_transcript_to_db(
    gene: Gene, transcript: str, ref_genome: ReferenceGenome
) -> Transcript:
    """
    Add each transcript to the database, with its gene.

    :param: gene, a Gene in need to linking to a transcript
    :param: transcript, the name of a transcript to add to the db
    :param: ref_genome, the ReferenceGenome of this version of the transcript

    :returns: Transcript instance, for the transcript added to the db
    """
    tx, _ = Transcript.objects.get_or_create(
        transcript=transcript, gene=gene, reference_genome=ref_genome
    )
    tx.save()
    return tx


def _add_transcript_categorisation_to_db(
    transcript: Transcript, data: dict[TranscriptRelease : dict[str:bool]]
) -> None:
    """
    Each transcript has been searched for in different transcript release files,
    to work out whether its a default clinical transcript or not.
    For example, if a transcript was found in MANE Select, causing the search for a
    transcript to stop, then the transcript will be 'clinical=True' in its linked
    'MANE Select' release, and 'clinical=None' in the linked releases of 'MANE Plus Clinical'
    and 'HGMD'.
    This function stores that search information, along with the transcript-release
    link.

    :param: the Transcript object
    :param: a dictionary containing TranscriptRelease objects (generally 1 for MANE Select,
    1 for MANE Plus Clinical and 1 for HGMD), each of which has a dictionary as its key.
    The nested dictionary contains the keys 'match_version', 'match_base' and 'clinical'
    which tells you whether the tx was found in the release (True/False) or not looked
    for (None).
    """
    TranscriptReleaseTranscript.objects.bulk_create(
        [
            TranscriptReleaseTranscript(
                transcript=transcript,
                release=release,
                match_version=data["match_version"],
                match_base=data["match_base"],
                default_clinical=data["clinical"],
            )
            for release, data in data.items()
        ],
        ignore_conflicts=True,
    )


def _get_clin_transcript_from_hgmd_files(
    hgnc_id: str, markname: dict, gene2refseq: dict
) -> tuple[str | None, str | None]:
    """
    Fetch the transcript linked to a particular gene in HGMD.
    First, need to find the gene's ID in the 'markname' table's file,
    then use the ID to find the gene's entries in the 'gene2refseq' table's file.
    Catch various error scenarios too.
    :param: hgnc_id of a gene
    :param: markname, a dictionary of information from a HGMD markname file
    :param: gene2refseq, a dict of information from a HGMD gene2refseq file
    :return: transcript linked to the gene in HGMD
    :return: error message if any
    """
    # HGMD database transcript search
    # hgmd write HGNC ID as XXXXX rather than HGNC:XXXXX
    short_hgnc_id = hgnc_id.replace("HGNC:", "")

    # Error states: hgnc id not in markname table / hgmd database,
    # or hgnc id has more than one entry
    if short_hgnc_id not in markname:
        err = f"{hgnc_id} not found in markname HGMD table"
        return None, err

    if len(markname[short_hgnc_id]) > 1:
        err = f"{hgnc_id} has two or more entries in markname HGMD table."
        return None, err

    # get the gene-id from markname table
    markname_gene_id = markname[short_hgnc_id][0]

    # Throw errors if the HGNC ID is None or pd.nan, if the gene ID from
    # markname isn't in gene2refseq, or if a gene has multiple entries in the
    # HGMD database (list with lists),
    # because assessment of clinical/non-clinical won't be possible.
    if not markname_gene_id or pd.isna(markname_gene_id):
        err = f"{hgnc_id} has no gene_id in markname table"
        return None, err

    markname_gene_id = markname_gene_id.strip()

    if markname_gene_id not in gene2refseq:
        err = f"{hgnc_id} with gene id {markname_gene_id} not in gene2refseq table"
        return None, err

    if len(gene2refseq[markname_gene_id]) > 1:
        joined_entries = [i[0] for i in gene2refseq[markname_gene_id]]
        err = f'{hgnc_id} has more than one transcript in the HGMD database: {",".join(joined_entries)}'
        return None, err

    # gene2refseq data for gene-id
    hgmd_base = gene2refseq[markname_gene_id][0][0]

    return hgmd_base, None


def _transcript_assign_to_source(
    tx: str,
    hgnc_id: str,
    mane_data: list[dict],
    markname_hgmd: dict,
    gene2refseq_hgmd: dict,
) -> tuple[dict, dict, dict, str | None]:
    """
    Carries out the logic for deciding whether a transcript is clinical, or non-clinical.
    Checks MANE first, then HGMD, to see if clinical status can be assigned

    :param: tx, the string name of a transcript to look for in sources
    :param: hgnc_id of a gene linked to the above transcript
    :param: mane_data, information extracted from a MANE file as a list of dicts
    :param: markname_hgmd, information extracted from HGMD's markname file as a dict
    :param: gene2refseq_hgmd, information extracted from HGMD's gene2refseq file as a dict

    :return: mane_select_data, containing info from MANE Select
    :return: mane_plus_clinical_data, containing info from MANE Plus Clinical
    :return: hgmd_data, containing info from HGMD
    :return: err, error message if any
    """
    mane_select_data = {"clinical": None, "match_base": None, "match_version": None}
    mane_plus_clinical_data = {
        "clinical": None,
        "match_base": None,
        "match_version": None,
    }
    hgmd_data = {"clinical": None, "match_base": None, "match_version": None}
    err = None

    tx_base = re.sub(r"\.[\d]+$", "", tx)

    # First, find the transcript in the MANE file data
    # Note that data in MANE can be Plus Clinical or Select
    mane_exact_match = [d for d in mane_data if d["RefSeq"] == tx]
    mane_base_match = [
        d for d in mane_data if re.sub(r"\.[\d]+$", "", d["RefSeq"]) == tx_base
    ]

    if mane_exact_match:
        if len(mane_exact_match) > 1:
            # check if we really need this transcript, because there's Panel-Gene
            # it's relevant to. If yes, throw an error, otherwise, just skip it
            rel_panels = PanelGene.objects.filter(gene__hgnc_id=hgnc_id)
            if len(rel_panels) != 0:
                raise ValueError(f"Transcript in MANE more than once: {tx}")
            else:
                err = f"Transcript in MANE more than once, can't resolve: {tx}"
                return mane_select_data, mane_plus_clinical_data, hgmd_data, err
        else:
            # determine whether it's MANE Select or Plus Clinical and return everything
            source = mane_exact_match[0]["MANE TYPE"]
            if str(source).lower() == "mane select":
                mane_select_data["clinical"] = True
                mane_select_data["match_base"] = True
                mane_select_data["match_version"] = True
            elif str(source).lower() == "mane plus clinical":
                mane_plus_clinical_data["clinical"] = True
                mane_plus_clinical_data["match_base"] = True
                mane_plus_clinical_data["match_version"] = True
            else:
                raise ValueError(
                    "MANE Type does not match MANE Select or MANE Plus Clinical"
                    " - check how mane_data has been set up"
                )
            return mane_select_data, mane_plus_clinical_data, hgmd_data, err

    # fall through to here if no exact match - see if there's a versionless match instead
    if mane_base_match:
        if len(mane_base_match) > 1:
            rel_panels = PanelGene.objects.filter(gene__hgnc_id=hgnc_id)
            if len(rel_panels) != 0:
                raise ValueError(f"Versionless ranscript in MANE more than once: {tx}")
            else:
                err = f"Versionless transcript in MANE more than once, can't resolve: {tx}"
                return mane_select_data, mane_plus_clinical_data, hgmd_data, err
        source = mane_base_match[0]["MANE TYPE"]
        if str(source).lower() == "mane select":
            mane_select_data["clinical"] = True
            mane_select_data["match_base"] = True
            mane_select_data["match_version"] = False
        elif str(source).lower() == "mane plus clinical":
            mane_plus_clinical_data["clinical"] = True
            mane_plus_clinical_data["match_base"] = True
            mane_plus_clinical_data["match_version"] = False
        else:
            raise ValueError(
                "MANE Type does not match MANE Select or MANE Plus Clinical"
                " - check how mane_data has been set up"
            )
        return mane_select_data, mane_plus_clinical_data, hgmd_data, err

    # hgnc id for the transcript's gene is not in MANE -
    # hgnc id for the transcript's gene is not in MANE -
    # instead, see which transcript is linked to the gene in HGMD
    hgmd_transcript_base, err = _get_clin_transcript_from_hgmd_files(
        hgnc_id, markname_hgmd, gene2refseq_hgmd
    )

    # does the HGMD transcript match the one we're currently looping through?
    # note HGMD doesn't have versions
    if tx_base == hgmd_transcript_base:
        hgmd_data["clinical"] = True
        hgmd_data["match_base"] = True
        hgmd_data["match_version"] = False

    return mane_select_data, mane_plus_clinical_data, hgmd_data, err


def _add_transcript_release_info_to_db(
    source: str, release_version: str, ref_genome: ReferenceGenome, files: dict
) -> None:
    """
    For each transcript release, make sure the source, release, and
    supporting files are added to the database.
    Note that the files parameter needs to be provided as a dict, in which keys are
    file types and values are external IDs.
    Errors will be raised if the release is already in the database AND its linked
    file IDs are different from what the user tried to input.

    :param: source, the name of a source of transcript information (e.g. MANE Select)
    :param: release_version, the version of the transcript release as entered by user
    :param: ref_genome, the ReferenceGenome used for this transcript release
    :param: files, a dictionary of files used to define the contents of each release.
    For example, a HGMD release might be defined by a markname and a gene2refseq file
    """
    errors = []

    # look up or create the source
    source_instance, _ = TranscriptSource.objects.get_or_create(source=source)

    # create the transcript release, or just get it
    # (this could happen if you upload an old release of 1 source, alongside a new release
    # of another source)
    release, release_created = TranscriptRelease.objects.get_or_create(
        source=source_instance,
        external_release_version=release_version,
        reference_genome=ref_genome,
    )

    if release_created:
        # Create the files from the dictionary provided, and link them to releases
        for file_type, file_id in files.items():
            file, _ = TranscriptFile.objects.get_or_create(
                file_id=file_id, file_type=file_type
            )

            file_release, _ = TranscriptReleaseTranscriptFile.objects.get_or_create(
                transcript_release=release, transcript_file=file
            )

    else:
        # if the release exists already, trigger an error if we are trying to link
        # new files to the existing release. If files are unchanged, do nothing
        for file_type, file_id in files.items():
            existing_file = TranscriptFile.objects.filter(file_id=file_id)
            if not existing_file:
                errors.append(
                    f"Transcript release {source} {release_version} "
                    f"already exists in db, but the uploaded file {file_id} is not "
                    f"in the db. Please review."
                )
            else:
                for file in existing_file:
                    links = TranscriptReleaseTranscriptFile.objects.filter(
                        transcript_file=file
                    )
                    for x in links:
                        if x.transcript_release != release:
                            errors.append(
                                f"Transcript file {file.file_id} "
                                f"already exists in db, but with a different transcript: "
                                f"{x.transcript_release}. Please review."
                            )
        # check we don't have files in the database for this release, that the user
        # ISN'T currently adding
        all_links_for_release = TranscriptReleaseTranscriptFile.objects.filter(
            transcript_release=release
        )
        for i in all_links_for_release:
            result = i.transcript_file.file_id
            if result not in files.values():
                errors.append(
                    f"Transcript file {result} "
                    f"is linked to the release in the db, but wasn't uploaded. "
                    f"Please review."
                )

    if errors:
        msg = " ".join(errors)
        raise ValueError(msg)

    return release


def _parse_reference_genome(ref_genome: str) -> str:
    """
    Convert reference genome into a standardised string.
    Throws error if this doesn't work.

    :param: reference genome string as provided by the user
    :param: reference genome string, post-normalisation
    """
    permitted_grch37 = ["hg19", "37", "grch37"]
    permitted_grch38 = ["hg38", "38", "grch38"]

    if ref_genome.lower() in permitted_grch37:
        return "GRCh37"
    elif ref_genome.lower() in permitted_grch38:
        return "GRCh38"
    else:
        raise ValueError(
            f"Please provide a valid reference genome,"
            f" such as {'; '.join(permitted_grch37)} or "
            f"{'; '.join(permitted_grch38)} - you provided {ref_genome}"
        )


# 'atomic' should ensure that any failure rolls back the entire attempt to seed
# transcripts - resetting the database to its start position
@transaction.atomic
def seed_transcripts(
    hgnc_filepath: str,
    hgnc_release: str,
    mane_filepath: str,
    mane_ext_id: str,
    mane_release: str,
    gff_filepath: str,
    g2refseq_filepath: str,
    g2refseq_ext_id: str,
    markname_filepath: str,
    markname_ext_id: str,
    hgmd_release: str,
    reference_genome: str,  # add reference genome metadata on transcript model
    write_error_log: bool,
) -> None:
    """
    Main function to seed transcripts
    Information on transcript releases (and accompanying files) are added to the db.
    Then every gene is added to the db, and each transcript is checked against the
    transcript releases, to work out whether or not its a clinical transcript.
    Finally, each transcript is linked to the releases, allowing the user to
    see what information was used in decision-making.
    :param hgnc_filepath: hgnc file path for gene IDs with current, past, and alias symbols
    :param mane_filepath: mane file path for transcripts
    :param mane_ext_id: mane file's ID in DNAnexus or other external platform
    :param mane_release: the mane release (e.g. v1) corresponding to the file in mane_filepath and mane_ext_id
    :param gff_filepath: gff file path
    :param g2refseq_filepath: gene2refseq file path
    :param g2refseq_ext_id: gene2refseq file's ID in DNAnexus or other external platform
    :param markname_filepath: markname file path
    :param markname_ext_id: markname file's ID in DNAnexus or other external platform
    :param hgmd_release: the hgmd release (e.g. v2) corresponding to the files in markname_filepath/markname_ext_id and gene2refseq_filepath/gene2refseq_ext_id
    :param reference_genome: the reference genome build, e.g. 37, 38
    :param write_error_log: write error log or not
    """
    # take today datetime
    current_datetime = dt.datetime.today().strftime("%Y%m%d")

    # prepare error log filename
    error_log: str = f"{current_datetime}_transcript_error.txt"

    # check reference genome makes sense, fetch it
    reference_genome_str = _parse_reference_genome(reference_genome)
    reference_genome, _ = ReferenceGenome.objects.get_or_create(
        reference_genome=reference_genome_str
    )

    # user - replace this with something sensible one day
    user = "transcripts_test_user"

    # files preparation
    hgnc_symbol_to_hgnc_id = _prepare_hgnc_file(hgnc_filepath, hgnc_release, user)
    mane_data = _prepare_mane_file(mane_filepath, hgnc_symbol_to_hgnc_id)
    gff = _prepare_gff_file(gff_filepath)
    gene2refseq_hgmd = _prepare_gene2refseq_file(g2refseq_filepath)
    markname_hgmd = _prepare_markname_file(markname_filepath)

    # set up the transcript release by adding it, any data sources, and any
    # supporting files to the database. Throw errors for repeated versions.
    mane_select_rel = _add_transcript_release_info_to_db(
        "MANE Select", mane_release, reference_genome, {"mane": mane_ext_id}
    )
    mane_plus_clinical_rel = _add_transcript_release_info_to_db(
        "MANE Plus Clinical", mane_release, reference_genome, {"mane": mane_ext_id}
    )
    hgmd_rel = _add_transcript_release_info_to_db(
        "HGMD",
        hgmd_release,
        reference_genome,
        {"hgmd_g2refseq": g2refseq_ext_id, "hgmd_markname": markname_ext_id},
    )

    # for record purpose (just in case)
    all_errors: list[str] = []

    # decide whether a transcript is clinical or not
    # add all this information to the database
    tx_starting = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"Start adding transcripts: {tx_starting}")
    for hgnc_id, transcripts in gff.items():
        gene = Gene.objects.get(hgnc_id=hgnc_id)
        # get deduplicated transcripts
        transcripts = set(transcripts)
        for tx in transcripts:
            # get information about how the transcript matches against MANE and HGMD
            (
                mane_select_data,
                mane_plus_clinical_data,
                hgmd_data,
                err,
            ) = _transcript_assign_to_source(
                tx, hgnc_id, mane_data, markname_hgmd, gene2refseq_hgmd
            )
            if err:
                all_errors.append(err)

            # add the transcript to the Transcript table
            transcript = _add_transcript_to_db(gene, tx, reference_genome)

            # link all the releases to the Transcript,
            # with the dictionaries containing match information
            releases_and_data_to_link = {
                mane_select_rel: mane_select_data,
                mane_plus_clinical_rel: mane_plus_clinical_data,
                hgmd_rel: hgmd_data,
            }
            _add_transcript_categorisation_to_db(transcript, releases_and_data_to_link)

    tx_ending = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"Finished adding transcripts to db: {tx_ending}")

    # write error log for those interested to see
    if write_error_log and all_errors:
        print(f"Writing error log to {error_log}")
        with open(error_log, "w") as f:
            f.write("\n".join(all_errors))
