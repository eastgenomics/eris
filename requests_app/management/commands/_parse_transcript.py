import collections
import datetime as dt
import pandas as pd

from requests_app.models import Gene, Transcript

# TODO: build-37 and build-38 transcripts?
# TODO: more informative transcript source column


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
    mane_file: str,
    hgnc_symbol_to_hgnc_id: dict[str, str],
) -> dict:
    """
    Read through MANE file and prepare
    dict of hgnc id to mane transcript

    Function inspiration from https://github.com/eastgenomics/g2t_ops/blob/main/g2t_ops/transcript_assigner.py#L36

    :param mane_file: mane file path
    :param hgnc_symbol_to_hgnc_id: dictionary of hgnc symbol to hgnc id
        to turn gene-id in mane to hgnc-id

    :return: dictionary of hgnc id to mane transcript
    """
    mane = pd.read_csv(mane_file)

    needed_cols = ["Gene", "MANE TYPE", "RefSeq StableID GRCh38 / GRCh37"]
    _sanity_check_cols_exist(mane, needed_cols, "MANE")

    filtered_mane = mane[
        mane["MANE TYPE"] == "MANE SELECT"
    ]  # only mane select transcripts

    filtered_mane["HGNC ID"] = filtered_mane["Gene"].map(hgnc_symbol_to_hgnc_id)

    return dict(
        zip(filtered_mane["HGNC ID"], filtered_mane["RefSeq StableID GRCh38 / GRCh37"])
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
    and generates a dict mapping of HGMD ID to list of [refcore, refversion]

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


def _add_gene_and_transcript_to_db(hgnc_id: str, transcripts: list, 
                                   reference_genome: str, source: str | None) -> None:
    """
    Add each gene to the database, with any transcripts associated with it.
    Source will often be something like "HGMD", but may be None for non-clinical transcripts
    """
    hgnc, _ = Gene.objects.get_or_create(hgnc_id=hgnc_id)

    for tx in transcripts:
        Transcript.objects.get_or_create(
            transcript=tx,
            source=source,
            gene_id=hgnc.id,
            reference_genome=reference_genome,
        )


def _markname_error_checker(short_hgnc_id: str, hgnc_id: str, markname_hgmd: dict) \
    -> str | None:
    """
    Check for show-stopping errors in the markname table - 
    a gene being absent or present more than once.
    """
    # hgnc id not in markname table / hgmd database, continue
    if short_hgnc_id not in markname_hgmd:
        err = f"{hgnc_id} not found in markname HGMD table"
        return err

    # hgnc id has more than one entry in markname table
    # this is a problem with no solution, return as non-clinical
    if len(markname_hgmd[short_hgnc_id]) > 1:
        err = f"{hgnc_id} have two or more entries in markname HGMD table."
        return err
    
    return None


def _markname_gene_id_error_checker(hgnc_id: str, markname_gene_id: str, gene2refseq_hgmd: dict) \
    -> str | None:
    """
    Throw errors if the HGNC ID is None or pd.nan, or if the gene ID from 
    markname isn't in gene2refseq, because assessment of clinical/non-clinical 
    won't be possible.
    """
    if not markname_gene_id or pd.isna(markname_gene_id):
        err = f"{hgnc_id} has no gene_id in markname table"
        return err

    if markname_gene_id not in gene2refseq_hgmd:
        err = f"{hgnc_id} with gene id {markname_gene_id} not in gene2refseq table"
        return err
    
    return None


def _transcript_assigner(tx: str, hgnc_id: str, gene_clinical_transcript: dict, 
                         mane_data: dict, markname_hgmd: dict, gene2refseq_hgmd: dict) \
                            -> tuple(bool, str, str | None):
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

    # if hgnc id already have a clinical transcript
    # any following transcripts will be non-clinical by default
    if hgnc_id in gene_clinical_transcript:
        if tx not in gene_clinical_transcript["hgnc_id"]:
            # a different transcript has already been assigned as clinical for this gene
            # any remaining transcripts will be NON clinical
            clinical = False
            return clinical, source, err

    tx_base, _ = tx.split(".")
    
    # if hgnc id in mane file
    if hgnc_id in mane_data:
        # MANE transcript search
        mane_tx = mane_data[hgnc_id]

        mane_base, _ = mane_tx.split(".")

        # compare transcript without the version
        if tx_base == mane_base:
            clinical = True
            source = "MANE"
            return clinical, source, err

    # HGMD database transcript search
    # hgmd write HGNC ID as XXXXX rather than HGNC:XXXXX
    shortened_hgnc_id = hgnc_id.replace("HGNC:", "")

    # markname is a table in HGMD database
    err = _markname_error_checker(shortened_hgnc_id, hgnc_id, markname_hgmd)
    if err:
        return clinical, source, err

    # get the gene-id from markname table
    markname_data = markname_hgmd[shortened_hgnc_id][0]
    markname_gene_id = markname_data.get("gene_id")

    err = _markname_gene_id_error_checker(hgnc_id, markname_gene_id, gene2refseq_hgmd)
    if err:
        return clinical, source, err

    # gene2refseq data for gene-id
    gene2refseq_data = gene2refseq_hgmd[markname_gene_id.strip()]

    if len(gene2refseq_data) > 1:
        err = f'{hgnc_id} have the following transcripts in HGMD database: {",".join(gene2refseq_hgmd)}'
        return clinical, source, err

    # only one entry in gene2refseq data
    hgmd_base, _ = gene2refseq_data[0]

    if tx_base == hgmd_base:
        clinical = True
        source = "HGMD"
    else:
        clinical = False
    return clinical, source, err


def seed_transcripts(
    hgnc_filepath: str,
    mane_filepath: str,
    gff_filepath: str,
    g2refseq_filepath: str,
    markname_filepath: str,
    reference_genome: str,  # add reference genome metadata on transcript model
    write_error_log: bool,
) -> None:
    """
    Main function to seed transcripts

    :param hgnc_filepath: hgnc file path
    :param mane_filepath: mane file path
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
        # make transcript into a list, because the transcript-adder is set up for a list
        transcript = [transcript] 
        _add_gene_and_transcript_to_db(hgnc_id, transcript, reference_genome, source)

    for hgnc_id, transcripts in gene_non_clinical_transcripts.items():
        _add_gene_and_transcript_to_db(hgnc_id, transcripts, reference_genome, None)

    # write error log for those interested to see
    if write_error_log:
        print(f"Writing error log to {error_log}")
        with open(error_log, "w") as f:
            for row in all_errors:
                f.write(f"{row}\n")


