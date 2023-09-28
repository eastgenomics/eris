import collections
import datetime as dt
import pandas as pd
import re

from requests_app.management.commands.tx_match import MatchType
from requests_app.models import Gene, Transcript, TranscriptRelease, TranscriptSource

# TODO: build-37 and build-38 transcripts?


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
        if gene.hgnc_id in hgnc_id_to_alias_symbols and not pd.isna(
            hgnc_id_to_alias_symbols[gene.hgnc_id]
        ).all():
            gene.alias_symbols = ",".join(hgnc_id_to_alias_symbols[gene.hgnc_id])

        gene.save()


def _prepare_hgnc_file(hgnc_file: str) -> dict[str, str]:
    """
    Read hgnc file, sanity-check it, and prepare four dictionaries:
    1. gene symbol to hgnc id
    2. hgnc id to approved symbol
    4. hgnc id to alias symbols

    Finally, update any metadata for existing genes in the Eris database - 
    if this has changed since the last HGNC upload.

    :param hgnc_file: hgnc file path
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

    _update_existing_gene_metadata_in_db(
        hgnc_id_to_approved_symbol, hgnc_id_to_alias_symbols
    )

    return hgnc_symbol_to_hgnc_id


def _sanity_check_cols_exist(df: pd.DataFrame, needed_cols: list, filename: str) -> None:
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
            errors.append(f"Missing column {x_col} from {filename} file - please check the file")

    errors = "; ".join(errors)
    assert not errors, errors


def _prepare_mane_file(
    mane_37_file: str,
    hgnc_symbol_to_hgnc_id: dict[str, str],
) -> dict:
    """
    Read through MANE files and prepare
    dict of hgnc id to mane transcript

    Function inspiration from https://github.com/eastgenomics/g2t_ops/blob/main/g2t_ops/transcript_assigner.py#L36

    :param mane_file: mane file path
    :param hgnc_symbol_to_hgnc_id: dictionary of hgnc symbol to hgnc id
        to turn gene-id in mane to hgnc-id

    :return: dictionary of hgnc id to mane transcript
    """
    mane = pd.read_csv(mane_37_file)

    needed_mane_cols = ["Gene", "MANE TYPE", "RefSeq StableID GRCh38 / GRCh37"]
    _sanity_check_cols_exist(mane, needed_mane_cols, "MANE")

    filtered_mane = mane[
        mane["MANE TYPE"] == "MANE SELECT"
    ]  # only mane select transcripts

    filtered_mane["HGNC ID"] = filtered_mane["Gene"].map(hgnc_symbol_to_hgnc_id)

    return dict(
        zip(filtered_mane["HGNC ID"], filtered_mane["RefSeq StableID GRCh38 / GRCh37"])
    )

def _prepare_mane_ftp_file(filepath: str, mane_version: str) -> dict:
    """
    Read FTP file to dataframe and sanity-check
    Assign the MANE version specified by the user for this release, if possible
    Return as a dict
    """   
    mane_ftp = pd.read_csv(filepath)

    needed_ftp_cols = ["MANE_Select_RefSeq_acc"]
    _sanity_check_cols_exist(mane_ftp, needed_ftp_cols, "MANE FTP")

    mane_ftp = mane_ftp.rename(columns={"MANE_Select_RefSeq_acc": "tx"})

    mane_ftp["mane_release"] = str(mane_version)
    mane_ftp["tx_base"] = mane_ftp["tx"].str.replace(r'\.[\d]+$', '', regex=True)
    mane_ftp["tx_version"] = mane_ftp["tx"].str.replace(r'^NM[\d]+\.', '', regex=True)

    final_df = mane_ftp[["tx", "tx_base", "tx_version", "mane_release"]].copy()

    # return only accession (with version) and MANE release cols
    return (
        final_df.to_dict(orient='records')
    )


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


def _assign_mane_release_to_tx(tx: str, tx_mane_release: list[dict]):
    """
    Given a transcript with version, and a list-of-dicts of transcript information made 
    from user input and a MANE FTP file, look up the MANE release.
    :return: MANE release version, or None if no match available.
    :return: type of match between transcript and MANE
    """
    tx_base = re.sub(r'\.[\d]+$', '', tx)
            
    # assign MANE release version from the dictionary of known-release FTP data
    perfect_match_with_mane = next((item for item in tx_mane_release if item['tx'] == tx), None)
    imperfect_match_with_mane = next((item for item in tx_mane_release 
                                        if item['tx_versionless'] == tx_base), None)
    if perfect_match_with_mane:
        release = perfect_match_with_mane["mane_release"]
        match_type = MatchType.complete_match()
    elif imperfect_match_with_mane:
        release = imperfect_match_with_mane["mane_release"]
        match_type = MatchType.versionless_match_only()
    else:
        release = None
        match_type = None
        # TODO: there's a logic hole to fix here - tx can be MANE but without release version?

    if release:
        # look up or create the source
        source, _ = TranscriptSource.objects.get_or_create(
            source = "MANE"
        )

        # look up or create the TranscriptRelease object
        transcript_release, _ = TranscriptRelease.objects.get_or_create(
            source=source,
            external_release_version=release,
            file_id=None,
            external_db_dump_date=None
            )
        
        return transcript_release, match_type
    else:
        return None, None


def _add_clinical_gene_and_transcript_to_db(hgnc_id: str, transcript: str, 
                                   reference_genome: str, source: str | None,
                                   tx_mane_release: dict) -> None:
    """
    Add each gene to the database, with its transcript.
    Source will often be something like "HGMD"
    """
    hgnc, _ = Gene.objects.get_or_create(hgnc_id=hgnc_id)

    # assign versions if possible
    if source == "MANE":
        release, match_type = _assign_mane_release_to_tx(transcript, tx_mane_release)

    elif source == "HGMD":
        #TODO: assign logic here - leaving as None for now
        release = match_type = None

    else:
        release = match_type = None

    # finally, create the transcript
    Transcript.objects.get_or_create(
        transcript=transcript,
        gene=hgnc.id,
        reference_genome=reference_genome,
        transcript_release=release,
        release_match_type=match_type
    )


def _add_non_clinical_gene_and_transcript_to_db(hgnc_id: str, transcripts: list, 
                                   reference_genome: str) -> None:
    """
    Add each gene to the database, with its transcript.
    """
    hgnc, _ = Gene.objects.get_or_create(hgnc_id=hgnc_id)

    for tx in transcripts:
        # create the transcript
        Transcript.objects.get_or_create(
            transcript=tx,
            gene=hgnc.id,
            reference_genome=reference_genome,
            transcript_release=None,
            release_match_type=None
        )


def _get_clin_transcript_from_hgmd_files(hgnc_id, markname: dict, gene2refseq: dict) \
    -> tuple[str | None, str | None]:
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
    # markname isn't in gene2refseq, or if a gene has multiple entries in the HGMD database (list with lists),
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


def _transcript_assigner(tx: str, hgnc_id: str, gene_clinical_transcript: dict, 
                         mane_data: dict, markname_hgmd: dict, gene2refseq_hgmd: dict) \
                            -> tuple[bool, str, str | None]:
    """
    Carries out the logic for deciding whether a transcript is clinical, or non-clinical.
    Checks MANE first, then HGMD, to see if clinical status can be assigned
    :return: clinical - boolean, True is clinical, False is non-clinical
    :return: source, for a clinical transcript
    :return: err - an error string, or None if no errors
    """
    clinical = False
    source = None
    err = None

    tx_base = re.sub(r'\.[\d]+$', '', tx)
    
    # if hgnc id already have a clinical transcript
    # any following transcripts will be non-clinical by default
    if hgnc_id in gene_clinical_transcript:
        # a different transcript has already been assigned as clinical for this gene
        # any remaining transcripts will be NON-clinical
        clinical = False
        return clinical, source, err
    
    # if hgnc id in mane file
    if hgnc_id in mane_data:
        # MANE transcript search
        mane_tx = mane_data[hgnc_id]
        mane_base = re.sub(r'\.[\d]+$', '', mane_tx)

        # compare transcript without the version
        if tx_base == mane_base:
            clinical = True
            source = "MANE"
            return clinical, source, err

    # hgnc id for the transcript's gene is not in MANE - 
    # instead, see which transcript is linked to the gene in HGMD
    hgmd_transcript_base, err = _get_clin_transcript_from_hgmd_files(hgnc_id, markname_hgmd, gene2refseq_hgmd)
    
    # does the HGMD transcript match the one we're currently looping through?
    if tx_base == hgmd_transcript_base:
        clinical = True
        source = "HGMD"
    
    return clinical, source, err


def seed_transcripts(
    hgnc_filepath: str,
    mane_filepath: str,
    mane_ftp_filepath: str,
    mane_release: str,
    gff_filepath: str,
    g2refseq_filepath: str,
    markname_filepath: str,
    reference_genome: str,  # add reference genome metadata on transcript model
    write_error_log: bool,
) -> None:
    """
    Main function to seed transcripts

    :param hgnc_filepath: hgnc file path
    :param mane_filepath: mane file path for GRCh37-compatible transcripts
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
    hgnc_symbol_to_hgnc_id = _prepare_hgnc_file(hgnc_filepath)
    mane_data = _prepare_mane_file(mane_filepath, hgnc_symbol_to_hgnc_id)
    mane_ftp_data = _prepare_mane_ftp_file(mane_ftp_filepath, mane_release)
    gff = _prepare_gff_file(gff_filepath)
    gene2refseq_hgmd = _prepare_gene2refseq_file(g2refseq_filepath)
    markname_hgmd = _prepare_markname_file(markname_filepath)


    # two dict for clinical and non-clinical tx assigment
    gene_clinical_transcript: dict[str, str] = {}
    gene_non_clinical_transcripts: dict[str, list] = collections.defaultdict(list)

    # for record purpose (just in case)
    all_errors: list[str] = []

    # decide whether a transcript is clinical or not, and append it to the corresponding dict
    # remove repeats of the transcript (with versions)
    for hgnc_id, transcripts in gff.items():
        # get deduplicated transcripts
        transcripts = set(transcripts)
        for tx in transcripts:
            clin, tx_source, err = \
                _transcript_assigner(tx, hgnc_id, gene_clinical_transcript, 
                         mane_data, markname_hgmd, gene2refseq_hgmd)
            if clin:
                gene_clinical_transcript[hgnc_id] = [tx, tx_source]
            else:
                gene_non_clinical_transcripts[hgnc_id].append(tx)
            if err:
                all_errors.append(err)

    # make genes - clinical or non-clinical - in db
    for hgnc_id, transcript_source in gene_clinical_transcript.items():       
        transcript, source = transcript_source
        _add_clinical_gene_and_transcript_to_db(hgnc_id, transcript, reference_genome, source,
                                       mane_ftp_data)

    for hgnc_id, transcripts in gene_non_clinical_transcripts.items():
        _add_non_clinical_gene_and_transcript_to_db(hgnc_id, transcripts, reference_genome)

    # write error log for those interested to see
    if write_error_log:
        print(f"Writing error log to {error_log}")
        with open(error_log, "w") as f:
            for row in all_errors:
                f.write(f"{row}\n")

