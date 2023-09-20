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

        # if hgnc id in dictionary and alias symbols not pd.nan
        if gene.hgnc_id in hgnc_id_to_alias_symbols and not pd.isna(
            hgnc_id_to_alias_symbols[gene.hgnc_id]
        ):
            gene.alias_symbols = ",".join(hgnc_id_to_alias_symbols[gene.hgnc_id])

        gene.save()


def _sanity_check_hgnc_file(hgnc: pd.DataFrame) -> None:
    """
    Check for expected fields in the HGNC file.

    :param: hgnc - a Pandas Dataframe
    :return: None 
    """
    # check if hgnc file has the correct columns
    assert "HGNC ID" in hgnc.columns, "Missing HGNC ID column. Check HGNC dump file"
    assert (
        "Approved symbol" in hgnc.columns
    ), "Missing Approved symbol column. Check HGNC dump file"
    assert (
        "Alias symbols" in hgnc.columns
    ), "Missing Alias symbols column. Check HGNC dump file"


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
    _sanity_check_hgnc_file(hgnc)

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

    assert "Gene" in mane.columns, "Missing Gene column. Check MANE file"
    assert "MANE TYPE" in mane.columns, "Missing MANE TYPE column. Check MANE file"
    assert (
        "RefSeq StableID GRCh38 / GRCh37" in mane.columns
    ), "Missing RefSeq column. Check MANE file"

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

    assert "hgncID" in markname.columns, "Missing hgncID column. Check markname file"

    return markname.groupby("hgncID")["gene_id"].apply(list).to_dict()


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
    gene_clinical_transcipt: dict[str, str] = {}
    gene_non_clinical_transcripts: dict[str, list] = collections.defaultdict(list)

    # for record purpose (just in case)
    all_errors: list[str] = []

    for hgnc_id, transcripts in gff.items():
        for tx in transcripts:
            # if hgnc id already have a clinical transcript
            # any following transcripts will be non-clinical by default
            if hgnc_id in gene_clinical_transcipt:
                # a transcript has been assigned either MANE or HGMD
                gene_non_clinical_transcripts[hgnc_id].append(tx)
                continue

            # comparing just the base, not version
            tx_base, _ = tx.split(".")

            # if hgnc id in mane file
            if hgnc_id in mane_data:
                # MANE transcript search
                mane_tx = mane_data[hgnc_id]

                mane_base, _ = mane_tx.split(".")

                # compare transcript without the version
                if tx_base == mane_base:
                    gene_clinical_transcipt[hgnc_id] = [tx, "MANE"]
                else:
                    gene_non_clinical_transcripts[hgnc_id].append(tx)

            else:
                # HGMD database transcript search

                # hgmd write HGNC ID as XXXXX rather than HGNC:XXXXX
                shortened_hgnc_id = hgnc_id.replace("HGNC:", "")

                # markname is a table in HGMD database
                # hgnc id not in markname table / hgmd database, continue
                if shortened_hgnc_id not in markname_hgmd:
                    all_errors.append(f"{hgnc_id} not found in HGMD table")
                    gene_non_clinical_transcripts[hgnc_id].append(tx)
                    continue

                # hgnc id has more than one entry in markname table
                # this is a problem with no solution, continue
                if len(markname_hgmd[shortened_hgnc_id]) > 2:
                    all_errors.append(f"{hgnc_id} have two entries in markname table.")
                    gene_non_clinical_transcripts[hgnc_id].append(tx)
                    continue

                # hgnc id has one entry in markname table
                markname_data = markname_hgmd[shortened_hgnc_id][0]

                # get the gene-id from markname table
                markname_gene_id = markname_data.get("gene_id")

                # the gene-id return None or pd.nan
                if not markname_gene_id or not pd.isna(markname_gene_id):
                    all_errors.append(f"{hgnc_id} has no gene_id in markname table")
                    gene_non_clinical_transcripts[hgnc_id].append(tx)
                    continue

                # gene-id returned from markname not in gene2refseq table
                # no point continuing
                if markname_gene_id not in gene2refseq_hgmd:
                    all_errors.append(
                        f"{hgnc_id} with gene id {markname_gene_id} not in gene2refseq table"
                    )
                    gene_non_clinical_transcripts[hgnc_id].append(tx)
                    continue

                # gene2refseq data for gene-id
                gene2refseq_data = gene2refseq_hgmd[markname_gene_id.strip()]

                # gene2refseq data has more than two entries
                # this is a problem with no solution, continue
                if len(gene2refseq_data) > 2:
                    all_errors.append(
                        f'{hgnc_id} have the following transcripts in HGMD database: {",".join(gene2refseq_hgmd)}'
                    )
                    gene_non_clinical_transcripts[hgnc_id].append(tx)
                    continue

                # only one entry in gene2refseq data
                else:
                    hgmd_base, _ = gene2refseq_data[0]

                    if tx_base == hgmd_base:
                        gene_clinical_transcipt[hgnc_id] = [tx, "HGMD"]
                    else:
                        gene_non_clinical_transcripts[hgnc_id].append(tx)

    # make genes - clinical or non-clinical - in db
    for hgnc_id, transcript_source in gene_clinical_transcipt.items():
        hgnc, _ = Gene.objects.get_or_create(hgnc_id=hgnc_id)

        transcript, source = transcript_source
        Transcript.objects.get_or_create(
            transcript=transcript,
            source=source,
            gene_id=hgnc.id,
            reference_genome=reference_genome,
        )

    for hgnc_id, transcripts in gene_non_clinical_transcripts.items():
        hgnc, _ = Gene.objects.get_or_create(hgnc_id=hgnc_id)

        for tx in transcripts:
            Transcript.objects.get_or_create(
                transcript=tx,
                source=None,
                gene_id=hgnc.id,
                reference_genome=reference_genome,
            )

    # write error log for those interested to see
    if write_error_log:
        print(f"Writing error log to {error_log}")
        with open(error_log, "w") as f:
            for row in all_errors:
                f.write(f"{row}\n")
