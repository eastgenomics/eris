import datetime as dt
import pandas as pd
import re
from django.db import transaction

pd.options.mode.chained_assignment = None  # default='warn'

from requests_app.models import (
    Gene,
    Transcript,
    TranscriptRelease,
    TranscriptSource,
    TranscriptFile,
    TranscriptReleaseTranscript,
    TranscriptReleaseTranscriptFile,
)


def _update_existing_gene_metadata_in_db(
    hgnc_id_to_approved_symbol,
    hgnc_id_to_alias_symbols,
) -> None:
    """
    Function to update gene metadata in db using hgnc dump prepared dictionaries

    :param hgnc_id_to_approved_symbol: dictionary of hgnc id to approved symbol
    :param hgnc_id_to_alias_symbols: dictionary of hgnc id to alias symbols
    """

    # updating gene symbols data in db using hgnc dump
    for gene in Gene.objects.all():
        if gene.hgnc_id in hgnc_id_to_approved_symbol:
            # if gene symbol in db differ from approved symbol in hgnc
            if gene.gene_symbol != hgnc_id_to_approved_symbol[gene.hgnc_id]:
                gene.gene_symbol = hgnc_id_to_approved_symbol[gene.hgnc_id]

        # if hgnc id in dictionary, and alias symbols are not all pd.nan
        if (
            gene.hgnc_id in hgnc_id_to_alias_symbols
            and not pd.isna(hgnc_id_to_alias_symbols[gene.hgnc_id]).all()
        ):
            gene.alias_symbols = ",".join(hgnc_id_to_alias_symbols[gene.hgnc_id])

        gene.save()


def _prepare_hgnc_file(hgnc_file: str) -> tuple[dict[str, str], list[dict]]:
    """
    Read hgnc file, sanity-check it, and prepare four dictionaries:
    1. gene symbol to hgnc id
    2. hgnc id to approved symbol
    4. hgnc id to alias symbols

    Finally, update any metadata for existing genes in the Eris database -
    if this has changed since the last HGNC upload.

    :param hgnc_file: hgnc file path
    :return: gene symbol to hgnc id dict
    :return: a list of dicts, each dict contains symbol AND alias AND hgnd_id
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

    _update_existing_gene_metadata_in_db(
        hgnc_id_to_approved_symbol, hgnc_id_to_alias_symbols
    )

    all_together = hgnc[needed_cols]
    all_together = all_together.to_dict("records")

    return hgnc_symbol_to_hgnc_id, all_together


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

    dict = min_cols.to_dict("records")

    return dict


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


def _prepare_markname_file(markname_file: str) -> dict:
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


def _add_transcript_to_db(gene: Gene, transcript: str, ref_genome: str) -> None:
    """
    Add each transcript to the database, with its gene.
    """
    tx, _ = Transcript.objects.get_or_create(
        transcript=transcript, gene=gene, reference_genome=ref_genome
    )
    tx.save()
    return tx


def _transcript_categorisation_bulk_upload(data):
    """
    Call a bulk upload of transcripts, saving time
    """
    # TODO: work out how to map data onto bulk upload
    objs = TranscriptReleaseTranscript.objects.bulk_create()


def _add_transcript_categorisation_to_db(
    transcript: Transcript, release: TranscriptRelease, data: dict
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
    """
    tx_link, _ = TranscriptReleaseTranscript.objects.get_or_create(
        transcript=transcript,
        release=release,
        match_version=data["match_version"],
        match_base=data["match_base"],
        default_clinical=data["clinical"],
    )


def _get_clin_transcript_from_hgmd_files(
    hgnc_id, markname: dict, gene2refseq: dict
) -> tuple[str | None, str | None]:
    """
    Fetch the transcript linked to a particular gene in HGMD.
    First, need to find the gene's ID in the 'markname' table's file,
    then use the ID to find the gene's entries in the 'gene2refseq' table's file.
    Catch various error scenarios too.
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
    :return: mane_select_data, containing info from MANE Select
    :return: mane_plus_clinical_data, containing info from MANE Plus Clinical
    :return: hgmd_data, containing info from HGMD
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
            raise ValueError(f"Transcript in MANE more than once: {tx}")
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
            return mane_select_data, mane_plus_clinical_data, hgmd_data, err

    # fall through to here if no exact match - see if there's a versionless match instead
    if mane_base_match:
        source = mane_base_match[0]["MANE TYPE"]
        if str(source).lower() == "mane select":
            mane_select_data["clinical"] = True
            mane_select_data["match_base"] = True
            mane_select_data["match_version"] = False
        elif str(source).lower() == "mane plus clinical":
            mane_plus_clinical_data["clinical"] = True
            mane_plus_clinical_data["match_base"] = True
            mane_plus_clinical_data["match_version"] = False
        return mane_select_data, mane_plus_clinical_data, hgmd_data, err

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
    source: str, release_version: str, ref_genome: str, files: dict
) -> None:
    """
    For each transcript release, make sure the source, release, and
    supporting files are added to the database.
    Note that the files parameter needs to be provided as a dict, in which keys are
    file types and values are external IDs.
    """

    # look up or create the source
    source, _ = TranscriptSource.objects.get_or_create(source=source)
    source.save()

    # create the transcript release, or just get it
    # (this could happen if you upload an old release of 1 source, alongside a new release
    # of another source)
    release, _ = TranscriptRelease.objects.get_or_create(
        source=source,
        external_release_version=release_version,
        reference_genome=ref_genome,
    )
    release.save()

    # Create the files from the dictionary provided, and link them to releases
    for file_type, file_id in files.items():
        file, _ = TranscriptFile.objects.get_or_create(
            file_id=file_id, file_type=file_type
        )
        file.save()

        file_release, _ = TranscriptReleaseTranscriptFile.objects.get_or_create(
            transcript_release=release, transcript_file=file
        )
        file_release.save()

    return release


def _get_or_create_gene_from_db(hgnc_id: str, hgnc_file_records: list[dict]) -> Gene:
    """
    If a gene exists in the db, fetch its record
    Otherwise, fill in its details
    Throw an error if the gene is in the HGNC data more than once
    """
    matches = [i for i in hgnc_file_records if i["HGNC ID"] == hgnc_id]
    if len(matches) > 1:
        raise ValueError("HGNC ID appears twice in HGNC file")
    elif len(matches) == 1:
        gene, _ = Gene.objects.get_or_create(
            hgnc_id=hgnc_id,
            gene_symbol=matches[0]["Approved symbol"],
            alias_symbols=matches[0]["Alias symbols"],
        )
        return gene
    else:
        # we don't know the symbol or alias IDs
        gene, _ = Gene.objects.get_or_create(hgnc_id=hgnc_id)
        return gene


# 'atomic' should ensure that any failure rolls back the entire attempt to seed
# transcripts - resetting the database to its start position
@transaction.atomic
def seed_transcripts(
    hgnc_filepath: str,
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
    :param hgnc_filepath: hgnc file path
    :param mane_filepath: mane file path for transcripts
    :param mane_ftp_filepath: mane file path for FTP file - known MANE version, but GRCh38
    :param gff_filepath: gff file path
    :param g2refseq_filepath: gene2refseq file path
    :param markname_filepath: markname file path
    :param write_error_log: write error log or not
    """
    # take today datetime
    current_datetime = dt.datetime.today().strftime("%Y%m%d")

    # prepare error log filename
    error_log: str = f"{current_datetime}_transcript_error.txt"

    # files preparation
    hgnc_symbol_to_hgnc_id, hgnc_with_info = _prepare_hgnc_file(hgnc_filepath)
    mane_data = _prepare_mane_file(mane_filepath, hgnc_symbol_to_hgnc_id)
    gff = _prepare_gff_file(gff_filepath)
    gene2refseq_hgmd = _prepare_gene2refseq_file(g2refseq_filepath)
    markname_hgmd = _prepare_markname_file(markname_filepath)

    # set up the transcript release by adding it, any data sources, and and
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
    for hgnc_id, transcripts in gff.items():
        gene = _get_or_create_gene_from_db(hgnc_id, hgnc_with_info)
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
            _transcript_categorisation_bulk_upload(data_to_link)
            for release, data in releases_and_data_to_link.items():
                _add_transcript_categorisation_to_db(transcript, release, data)

    # write error log for those interested to see
    if write_error_log:
        print(f"Writing error log to {error_log}")
        with open(error_log, "w") as f:
            for row in all_errors:
                f.write(f"{row}\n")
