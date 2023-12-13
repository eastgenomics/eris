import datetime as dt
import pandas as pd
import collections
import re
from django.db import transaction
from packaging.version import Version

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
    GffRelease,
    TranscriptGffRelease,
    TranscriptGffReleaseHistory,
)


def _update_existing_gene_metadata_symbol_in_db(
    hgnc_id_to_symbol: dict[str:str], hgnc_release: HgncRelease, user: str
) -> None:
    """
    Function to update gene metadata in db using a hgnc dump prepared dictionary
    Updates approved symbol if that has changed.
    To speed up the function, we utilise looping over lists-of-dictionaries,
    and bulk updates in some spots.

    :param hgnc_id_to_symbol: dictionary of hgnc id to approved symbol
    :param hgnc_release: the HgncRelease for the currently-uploaded HGNC file
    :param user: currently a string to describe the user
    """
    gene_symbol_updates = []

    # queue up genes which need updating because their approved symbols have
    # changed in HGNC
    for hgnc_id, symbols in hgnc_id_to_symbol.items():
        gene = Gene.objects.get(hgnc_id=hgnc_id)
        gene.gene_symbol = symbols["new"]
        gene_symbol_updates.append(gene)

    # bulk update the changed genes
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"Start bulk-updating {len(gene_symbol_updates)} gene symbols: {now}")
    Gene.objects.bulk_update(gene_symbol_updates, ["gene_symbol"])

    # for each changed gene, link to release and add a note
    for gene in gene_symbol_updates:
        gene_hgnc_release = GeneHgncRelease.objects.create(
            gene=gene, hgnc_release=hgnc_release
        )

        # get the old and new symbols for history-notes
        new = hgnc_id_to_symbol[gene.hgnc_id]["new"]
        old = hgnc_id_to_symbol[gene.hgnc_id]["old"]

        GeneHgncReleaseHistory.objects.create(
            gene_hgnc_release=gene_hgnc_release,
            note=History.gene_hgnc_release_approved_symbol_change(old, new),
            user=user,
        )


def _update_existing_gene_metadata_aliases_in_db(
    hgnc_id_to_alias_symbols: dict[str:str], hgnc_release: HgncRelease, user: str
) -> None:
    """
    Function to update gene metadata in db using hgnc dump prepared dictionaries
    Updates alias symbols if those have changed.
    To speed up the function, we utilise looping over lists-of-dictionaries,
    and bulk updates.

    :param hgnc_id_to_alias_symbols: dictionary of hgnc id to alias symbol
    :param hgnc_release: the HgncRelease for the currently-uploaded HGNC file
    :param user: currently a string to describe the user
    """
    gene_alias_updates = []

    for changed_gene, new_alias in hgnc_id_to_alias_symbols.items():
        gene = Gene.objects.get(hgnc_id=changed_gene)
        gene.alias_symbols = new_alias["new"]
        gene_alias_updates.append(gene)

    now = datetime.datetime.now().strftime("%H:%M:%S")
    f"Start bulk-updating {len(gene_alias_updates)} gene alias: {now}"
    Gene.objects.bulk_update(gene_alias_updates, ["alias_symbols"])

    # for each changed gene, link to release and add a note
    for gene in gene_alias_updates:
        gene_hgnc_release, _ = GeneHgncRelease.objects.get_or_create(
            gene=gene, hgnc_release=hgnc_release
        )

        # get the old and new aliases for history-logging
        new = hgnc_id_to_alias_symbols[gene.hgnc_id]["new"]
        old = hgnc_id_to_alias_symbols[gene.hgnc_id]["old"]

        GeneHgncReleaseHistory.objects.create(
            gene_hgnc_release=gene_hgnc_release,
            note=History.gene_hgnc_release_alias_symbol_change(old, new),
            user=user,
        )


def _link_unchanged_genes_to_new_release(
    unchanged_genes: list, hgnc_release: HgncRelease, user: str
):
    """
    If a gene wasn't changed in a HGNC release, link it to the new release with a note,
    so we know the gene is still current

    :param unchanged_gene: a list of HGNC_IDs of unchanged genes
    :param hgnc_release: a HgncRelease object of the current release
    :param str: the name of the user making the changed
    """

    print(
        f"Linking {len(unchanged_genes)} unchanged genes to new HGNC release v{hgnc_release.hgnc_release}"
    )

    for hgnc_id in unchanged_genes:
        gene = Gene.objects.get(hgnc_id=hgnc_id)

        gene_hgnc_release, release_created = GeneHgncRelease.objects.get_or_create(
            gene=gene, hgnc_release=hgnc_release
        )

        # if a new gene-release link was made, log it in history
        # if it existed already, don't log it
        if release_created:
            GeneHgncReleaseHistory.objects.create(
                gene_hgnc_release=gene_hgnc_release,
                note=History.gene_hgnc_release_present(),
                user=user,
            )


def _add_new_genes_to_db(
    new_genes: dict[str:str], hgnc_release: HgncRelease, user: str
) -> None:
    """
    If a gene exists in the HGNC file, but does NOT exist in the db, make it.
    Link the gene to the HGNC file's release, to help with auditing.
    To speed up the function, we utilise looping over lists-of-dictionaries,
    and bulk updates in some places.

    :param new_genes: a list of dicts, one per gene, with keys 'hgnc_id' 'symbol' and 'alias'
    :param hgnc_release: the HgncRelease for the currently-uploaded HGNC file
    :param user: currently a string to describe the user
    """
    genes_to_create = []

    for gene in new_genes:
        new_gene = Gene(
            hgnc_id=gene["hgnc_id"],
            gene_symbol=gene["symbol"],
            alias_symbols=gene["alias"],
        )
        genes_to_create.append(new_gene)

    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"Start {len(new_genes)} gene bulk create: {now}")
    new_genes = Gene.objects.bulk_create(genes_to_create)

    # for each NEW gene, link to release and add a note
    for gene in new_genes:
        gene_hgnc_release = GeneHgncRelease.objects.create(
            gene=gene, hgnc_release=hgnc_release
        )

        GeneHgncReleaseHistory.objects.create(
            gene_hgnc_release=gene_hgnc_release,
            note=History.gene_hgnc_release_new(),
            user=user,
        )


def _make_hgnc_gene_sets(
    hgnc_id_to_symbol: dict[str, str], hgnc_id_to_alias: dict[str, list[str]]
) -> tuple[list, dict, dict, list]:
    """
    Sort genes into:
    - those which are not yet in the Gene table, but are in the HGNC release
    - those which are both already in the Gene table and in the HGNC release:
        - those that have changed in the HGNC release:
            - symbol changes
            - alias changes
        - those that are unchanged in the HGNC release

    These sets are then used by downstream functions to update the database

    :param hgnc_id_to_approved_symbol: a dictionary of HGNC_ID to the approved symbols in the new HGNC release
    :param hgnc_id_to_alias_symbol: a dictionary of HGNC_ID to the list of alias symbols in the new HGNC release

    :return new_hgncs: a list of dicts, one per new gene, with keys 'hgnc_id' 'symbol' and 'alias'
    :return hgnc_symbol_changed: a dict-of-dicts of genes with changed symbols, keys are hgnc_ids, the nested dict has 'old' and 'new 'aliases
    :return hgnc_alias_changed: a dict-of-dicts of genes with changed alias, keys are hgnc_ids, the nested dict has 'old' and 'new 'aliases
    :return hgnc_unchanged: a list of HGNC IDs for genes which are in the release, but unchanged
    """
    # get every HGNC ID in the HGNC file
    all_hgnc_in_approved = list(hgnc_id_to_symbol.keys())
    all_hgnc_in_alias = list(hgnc_id_to_alias.keys())
    all_hgnc_file_entries = all_hgnc_in_alias + all_hgnc_in_approved

    # for hgnc_ids which already exist in the database, get the ones which have changed
    # and ones which haven't changed
    genes_in_db: list[Gene] = Gene.objects.all()
    hgnc_symbol_changed = collections.defaultdict(dict)
    hgnc_alias_changed = collections.defaultdict(dict)

    hgnc_unchanged = []

    for gene in genes_in_db:
        hgnc_id = gene.hgnc_id
        current_gene_symbol = (
            gene.gene_symbol.strip().upper() if gene.gene_symbol else None
        )  # gene symbol in current gene in db can be None
        potential_new_gene_symbol = hgnc_id_to_symbol.get(hgnc_id)  # might be None

        symbol_change = False
        alias_change = False

        # check symbol change
        if potential_new_gene_symbol:
            if current_gene_symbol != potential_new_gene_symbol.strip().upper():
                # add to a list of symbol-changed HGNCs
                symbol_change = True
                hgnc_symbol_changed[gene.hgnc_id]["old"] = current_gene_symbol
                hgnc_symbol_changed[gene.hgnc_id][
                    "new"
                ] = potential_new_gene_symbol.strip().upper()

        # check alias change
        if gene.hgnc_id in hgnc_id_to_alias:
            resolved_alias = _resolve_alias(hgnc_id_to_alias[gene.hgnc_id])
            if gene.alias_symbols != resolved_alias:
                # add to a list of alias-changed HGNCs
                alias_change = True
                hgnc_alias_changed[gene.hgnc_id]["old"] = gene.alias_symbols
                hgnc_alias_changed[gene.hgnc_id]["new"] = resolved_alias

        # if the database gene is unchanged, add it to an 'unchanged' list if it's in HGNC file
        if (
            not symbol_change
            and not alias_change
            and gene.hgnc_id in all_hgnc_file_entries
        ):
            hgnc_unchanged.append(gene.hgnc_id)

    # get HGNC IDs which are in the HGNC file, but not yet in db
    new_hgncs = set(all_hgnc_file_entries) - set([i.hgnc_id for i in genes_in_db])
    new_hgncs = [
        {
            "hgnc_id": hgnc_id,
            "symbol": hgnc_id_to_symbol.get(hgnc_id),
            "alias": _resolve_alias(hgnc_id_to_alias.get(hgnc_id)),
        }
        for hgnc_id in new_hgncs
    ]

    return new_hgncs, hgnc_symbol_changed, hgnc_alias_changed, hgnc_unchanged


def _resolve_alias(start_alias: list[str]) -> str | None:
    """
    Joins aliases, handling the case where an alias contains pd.na
    Mostly exists because this was originally a one-liner, but I started
    struggling to read it.
    :param start_alias: the list of alias names. It contains either strings or
    a single np.nan value.
    :param processed_alias: the alias returned as a single joined string, or, None
    if the input was blank/just np.nan values.
    """
    if not start_alias:
        return None

    # sort, deduplicate, and strip whitespace
    aliases = sorted(
        list(set([alias.strip() for alias in start_alias if alias.strip()]))
    )

    if not aliases:
        return None

    return ",".join(aliases)


def _prepare_hgnc_file(hgnc_file: str, hgnc_version: str, user: str) -> dict[str, str]:
    """
    Read a hgnc file and sanity-check it
    If the HGNC version is new, add it to the database
    For each HGNC ID in the HGNC file, determine which are brand-new genes, which are genes in need
    of updating, and which genes already exist in the database.
    Finally, use that categorised data to update the Eris database, linking any changes
    to this HGNC file release.
    Return a dictionary of every HGNC ID: symbol in the current file.

    :param hgnc_file: hgnc file path
    :param hgnc_version: a string describing the in-house-assigned release version of
    the HGNC file
    :param user: str, the user's name

    :return: gene symbol to hgnc id dict
    """
    print("Preparing HGNC files")
    hgnc: pd.DataFrame = pd.read_csv(hgnc_file, delimiter="\t")

    needed_cols = ["HGNC ID", "Approved symbol", "Alias symbols"]
    _sanity_check_cols_exist(hgnc, needed_cols, "HGNC dump")

    # strip whitespace as a precaution
    hgnc["Approved symbol"] = hgnc["Approved symbol"].str.strip()
    hgnc["HGNC ID"] = hgnc["HGNC ID"].str.strip()

    # prepare dictionary files
    hgnc1 = hgnc.dropna(subset=["Approved symbol"])
    hgnc_approved_symbol_to_hgnc_id = dict(
        zip(hgnc1["Approved symbol"], hgnc1["HGNC ID"])
    )
    hgnc_id_to_approved_symbol = dict(zip(hgnc1["HGNC ID"], hgnc1["Approved symbol"]))

    # dataframe cleaning to drop NA values in alias symbols
    hgnc.dropna(subset=["Alias symbols"], inplace=True)
    hgnc["HGNC ID"] = hgnc["HGNC ID"].str.strip()  # remove whitespace in HGNC ID

    hgnc_id_to_alias_symbols: dict[str, list[str]] = (
        hgnc.groupby("HGNC ID")["Alias symbols"]
        .agg(lambda x: x.str.split(","))
        .to_dict()
    )

    # create a HGNC release
    # the same HGNC release version can be used at different transcript seed times
    hgnc_release, release_created = HgncRelease.objects.get_or_create(
        hgnc_release=hgnc_version
    )

    # get all possible HGNC IDs from the HGNC file, and compare to what's already in the database,
    # to sort them into those which need adding and those which need editing
    new_genes, symbol_changed, alias_changed, unchanged_genes = _make_hgnc_gene_sets(
        hgnc_id_to_approved_symbol, hgnc_id_to_alias_symbols
    )

    # make edits and release links to pre-existing genes, and add genes which are new in the HGNC file
    with transaction.atomic():
        if symbol_changed:
            _update_existing_gene_metadata_symbol_in_db(
                symbol_changed, hgnc_release, user
            )

        if alias_changed:
            _update_existing_gene_metadata_aliases_in_db(
                alias_changed, hgnc_release, user
            )

        if release_created:  # linked unchanged only when there's new release created
            _link_unchanged_genes_to_new_release(unchanged_genes, hgnc_release, user)

        if new_genes:
            _add_new_genes_to_db(new_genes, hgnc_release, user)

    return hgnc_approved_symbol_to_hgnc_id


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
        if x_col not in df.columns:
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


def _prepare_gff_file(gff_file: str, gff_version: str, user: str) -> dict[str, list]:
    """
    Read through gff files (from DNANexus)
    and prepare dict of hgnc id to list of transcripts

    :param gff_file: gff file path
    :param hgnc_version: a string describing the in-house-assigned release version of
    the gff file
    :param user: str, the user's name

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


def _add_transcript_to_db_with_gff_release(
    gene: Gene,
    transcript: str,
    ref_genome: ReferenceGenome,
    gff_release: GffRelease,
    user: str,
) -> Transcript:
    """
    Add each transcript to the database, with its gene.
    Link it to the current GFF release, and log history of the change.

    :param: gene, a Gene in need to linking to a transcript
    :param: transcript, the name of a transcript to add to the db
    :param: ref_genome, the ReferenceGenome of this version of the transcript
    :param: gff_release, the GffRelease of this version of the GFF file
    :param: user, a string representing the user carrying out the upload

    :returns: Transcript instance, for the transcript added to the db
    """
    tx, tx_created = Transcript.objects.get_or_create(
        transcript=transcript, gene=gene, reference_genome=ref_genome
    )

    tx_gff, tx_gff_created = TranscriptGffRelease.objects.get_or_create(
        transcript=tx, gff_release=gff_release
    )

    if tx_created:
        message = History.tx_gff_release_new()
    elif tx_gff_created:
        message = History.tx_gff_release_present()
    else:
        # neither transcript nor its GFF link are new - no need to add history info
        return tx

    TranscriptGffReleaseHistory.objects.get_or_create(
        transcript_gff=tx_gff, note=message, user=user
    )

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


def _add_gff_release_info_to_db(
    gff_release: str, reference_genome: ReferenceGenome
) -> GffRelease:
    """
    Add a release version to the database for the GFF file.
    Add reference genome information.
    :param gff_release: string of the release version of the GFF file
    :param reference_genome: a ReferenceGenome object to associate with this GFF file
    :return gff_release: a GffRelease instance
    """
    gff_release, _ = GffRelease.objects.get_or_create(
        gff_release=gff_release, reference_genome=reference_genome
    )
    return gff_release


def _link_release_to_file_id(
    release: TranscriptRelease, file_id: str, file_type: str
) -> None:
    """
    create TranscriptFile and link to TranscriptRelease
    through TranscriptReleaseTranscriptFile

    :param release: a TranscriptRelease object
    :param file_id: a string representing the file ID
    :param file_type: a string representing the file type (e.g. 'MANE Select')
    """
    transcript_file, _ = TranscriptFile.objects.get_or_create(
        file_id=file_id, file_type=file_type
    )

    TranscriptReleaseTranscriptFile.objects.get_or_create(
        transcript_release=release, transcript_file=transcript_file
    )


def _add_transcript_release_info_to_db(
    source: str,
    release_version: str,
    ref_genome: ReferenceGenome,
    files: dict[str, str],
) -> TranscriptRelease:
    """
    For each transcript release, make sure the source, release, and
    supporting files are added to the database.
    Note that the files parameter needs to be provided as a dict, in which keys are
    file types and values are external IDs.

    Error will be raised if the file-id is already linked to another release, source and ref genome
    of a particular file type (e.g. MANE Select)

    Example of error scenario:
        - MANE Select release 0.92 is linked to file-id 12345 in db
        - You uploaded MANE Select release 0.93 but with file-id 12345
        - This will raise a ValueError because the file-id can't be both v0.92 and v0.93

    :param: source, the name of a source of transcript information (e.g. MANE Select)
    :param: release_version, the version of the transcript release as entered by user
    :param: ref_genome, the ReferenceGenome used for this transcript release
    :param: files, a dictionary of files used to define the contents of each release.
    For example, a HGMD release might be defined by a markname and a gene2refseq file

    :return: a TranscriptRelease instance
    """

    # look up or create the source
    source_instance, _ = TranscriptSource.objects.get_or_create(source=source)

    # create the transcript release, or just get it
    # (this could happen if you upload an old release of 1 source, alongside a new release
    # of another source)
    tx_release, _ = TranscriptRelease.objects.get_or_create(
        source=source_instance,
        release=release_version,
        reference_genome=ref_genome,
    )

    for file_type, file_id in files.items():
        # NOTE: check if release, source and ref genome OF A FILE TYPE is already linked to another file-id
        # if so, raise an error, else pass
        # the file-id might still be linked to its previous release, source and ref genome - which is completely valid

        tx_release_file_ids = TranscriptReleaseTranscriptFile.objects.filter(
            transcript_release_id=tx_release.id,
            transcript_file_id__file_type=file_type,
        ).values("transcript_file_id__file_id", "transcript_file_id__file_type")
        # there should only be ONE link of file-id to one RELEASE of a particular file type

        # a different (release, source, ref genome) combination should have a different file-id
        if tx_release_file_ids:
            if (
                tx_release_file_ids[0]["transcript_file_id__file_id"] != file_id
                or tx_release_file_ids[0]["transcript_file_id__file_type"] != file_type
            ):
                raise ValueError(
                    f"The provided file-id '{file_id}' and file-type '{file_type}' is already linked to another "
                    "release, source and ref genome in the db:\n"
                    f"Release version: {release_version}\n"
                    f"Source: {source}.\n"
                    f"Ref genome: {ref_genome.reference_genome}.\n"
                    f'File type: {tx_release_file_ids[0]["transcript_file_id__file_type"]}\n'
                    f'File id: {tx_release_file_ids[0]["transcript_file_id__file_id"]}'
                )

        _link_release_to_file_id(tx_release, file_id, file_type)

    return tx_release


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


def _get_latest_hgnc_release() -> Version | None:
    """
    Get the latest release in HgncRelease, using packaging.version to handle version formatting
    which isn't 100% consistent. Return None if the table has no matching results.

    :returns: latest version in database
    """
    hgncs = HgncRelease.objects.all()

    return max([Version(v.hgnc_release) for v in hgncs]) if hgncs else None


def _get_latest_gff_release(ref_genome: ReferenceGenome) -> Version | None:
    """
    Get the latest GFF release in GffRelease for a given reference genome,
      using packaging.version because the version formatting
    isn't 100% consistent. Return None if the table has no matching results.

    :param reference_genome: a ReferenceGenome object corresponding to user input
    :returns: latest version in database
    """
    gffs = GffRelease.objects.filter(reference_genome=ref_genome)

    return max([Version(v.gff_release) for v in gffs]) if gffs else None


def _get_latest_transcript_release(
    source: Version, ref_genome: ReferenceGenome
) -> Version:
    """
    Get the latest release in the TranscriptRelease table for a given source
    and reference genome. Return None if the table has no matching results.

    :param source: a source string such as 'HGMD', 'MANE Plus Clinical' or 'MANE Select'
    :param reference_genome: a ReferenceGenome object corresponding to user input
    :returns: latest version in database
    """
    tx_releases = TranscriptRelease.objects.filter(source__source=source).filter(
        reference_genome=ref_genome
    )

    return (
        max([Version(v.release) for v in tx_releases])
        if tx_releases
        else Version("0.0a")
    )


def _check_for_transcript_seeding_version_regression(
    hgnc_release: str,
    gff_release: str,
    mane_release: str,
    hgmd_release: str,
    reference_genome: ReferenceGenome,
) -> None:
    """
    For any releases needed for transcript seeding,
    get the latest ones in the database, and check that the user hasn't entered an older one.
    Throw error messages if one or more releases are older than expect, and quit out.
    Otherwise, continue.

    :param hgnc_release: user-input HGNC release version
    :param gff_release: user-input GFF release version
    :param mane_release: user-input MANE release version
    :param hgmd_release: user-input HGMD release version
    """

    input_versions = {
        "HGNC": hgnc_release,
        "GFF": gff_release,
        "MANE": mane_release,
        "HGMD": hgmd_release,
    }

    # find the latest releases in the db
    latest_db_versions = {
        "HGNC": _get_latest_hgnc_release(),
        "GFF": _get_latest_gff_release(reference_genome),
        "MANE": max(
            [
                _get_latest_transcript_release("MANE Select", reference_genome),
                _get_latest_transcript_release("MANE Plus Clinical", reference_genome),
            ]
        ),
        "HGMD": _get_latest_transcript_release("HGMD", reference_genome),
    }

    error = "\n".join(
        [
            f"Provided {source} version {input_version} is a lower version than v{str(latest_db_versions[source])} in the db"
            for source, input_version in input_versions.items()
            if latest_db_versions[source] and Version(input_version) < latest_db_versions[source]
        ]
    )

    if error:
        raise ValueError("Abandoning input:\n" + error)


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
    gff_release: str,
    g2refseq_filepath: str,
    g2refseq_ext_id: str,
    markname_filepath: str,
    markname_ext_id: str,
    hgmd_release: str,
    reference_genome: str,
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
    :param hgnc_release: the hgnc release (e.g. v1) corresponding to the file in hgnc_filepath
    :param mane_filepath: mane file path for transcripts
    :param mane_ext_id: mane file's ID in DNAnexus or other external platform
    :param mane_release: the mane release (e.g. v1) corresponding to the file in mane_filepath and mane_ext_id
    :param gff_filepath: gff file path
    :param gff_release: the gff release (e.g. v2) corresponding to the file in gff_filepath
    :param g2refseq_filepath: gene2refseq file path
    :param g2refseq_ext_id: gene2refseq file's ID in DNAnexus or other external platform
    :param markname_filepath: markname file path
    :param markname_ext_id: markname file's ID in DNAnexus or other external platform
    :param hgmd_release: the hgmd release (e.g. v2) corresponding to the files in markname_filepath/markname_ext_id and gene2refseq_filepath/gene2refseq_ext_id
    :param reference_genome: the reference genome build, e.g. 37, 38
    :param write_error_log: write error log or not
    """
    # take today's datetime
    current_datetime = dt.datetime.today().strftime("%Y%m%d")

    # prepare error log filename
    error_log: str = f"{current_datetime}_transcript_error.txt"

    # check reference genome makes sense, fetch it
    reference_genome_str = _parse_reference_genome(reference_genome)
    reference_genome, _ = ReferenceGenome.objects.get_or_create(
        reference_genome=reference_genome_str
    )

    # throw errors if the release versions are older than those already in the db
    _check_for_transcript_seeding_version_regression(
        hgnc_release, gff_release, mane_release, hgmd_release, reference_genome
    )

    # TODO: user - replace this with something sensible one day
    user = "init_v1_user"

    # files preparation - parsing the files, and adding release versioning to the database
    hgnc_symbol_to_hgnc_id = _prepare_hgnc_file(hgnc_filepath, hgnc_release, user)
    mane_data = _prepare_mane_file(mane_filepath, hgnc_symbol_to_hgnc_id)
    gff = _prepare_gff_file(gff_filepath, gff_release, user)
    gene2refseq_hgmd = _prepare_gene2refseq_file(g2refseq_filepath)
    markname_hgmd = _prepare_markname_file(markname_filepath)

    # set up the transcript release by adding it, any data sources, and any
    # supporting files to the database. Throw errors for repeated versions.

    gff_release = _add_gff_release_info_to_db(gff_release, reference_genome)

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
        for tx in set(transcripts):
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
            transcript = _add_transcript_to_db_with_gff_release(
                gene, tx, reference_genome, gff_release, user
            )

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
