import csv
import collections
import datetime as dt

from panel_requests.requests_app.models import Gene, Transcript


def seed_transcripts(
    hgnc_file: str,
    mane_file: str,
    gff_file: str,
    g2refseq_file: str,
    markname_file: str,
    write_error_log: bool,
) -> None:
    current_datetime = dt.datetime.today().strftime("%Y%m%d")
    error_log: str = f"{current_datetime}_transcript_error.txt"

    # gene symbols : hgnc id
    hgnc_symbols_to_hgnc_id: dict[str, str] = {}
    hgnc_id_to_approved_symbol: dict[str, str] = {}
    hgnc_id_to_previous_symbols: dict[str, list] = collections.defaultdict(
        list
    )
    hgnc_id_to_alias_symbols: dict[str, list] = collections.defaultdict(list)

    with open(hgnc_file, "r") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if (
                "HGNC ID" not in row
                or "Approved symbol" not in row
                or "Previous symbols" not in row
                or "Alias symbols" not in row
            ):
                raise ValueError(
                    "Check HGNC dump columns headers. Error with HGNC dump file"
                )

            hgnc = row["HGNC ID"].strip()
            approved_symbol = row["Approved symbol"].strip()
            previous_symbols = row["Previous symbols"].strip()
            alias_symbols = row["Alias symbols"].strip()

            if approved_symbol:
                if (
                    approved_symbol not in hgnc_symbols_to_hgnc_id
                    and approved_symbol.strip()
                ):
                    hgnc_symbols_to_hgnc_id[approved_symbol] = hgnc
                    hgnc_id_to_approved_symbol[hgnc] = approved_symbol

            if previous_symbols:
                for symbol in previous_symbols.split(","):
                    if (
                        symbol not in hgnc_symbols_to_hgnc_id
                        and symbol.strip()
                    ):
                        hgnc_symbols_to_hgnc_id[symbol.strip()] = hgnc
                        hgnc_id_to_previous_symbols[hgnc].append(
                            symbol.strip()
                        )

            if alias_symbols:
                for symbol in alias_symbols.split(","):
                    if (
                        symbol not in hgnc_symbols_to_hgnc_id
                        and symbol.strip()
                    ):
                        hgnc_symbols_to_hgnc_id[symbol.strip()] = hgnc
                        hgnc_id_to_alias_symbols[hgnc].append(symbol.strip())

    # updating gene symbols data in database using hgnc
    for gene in Gene.objects.all():
        if gene.hgnc_id in hgnc_id_to_approved_symbol:
            gene.gene_symbol = hgnc_id_to_approved_symbol[gene.hgnc_id]
        else:
            gene.gene_symbol = None

        if gene.hgnc_id in hgnc_id_to_alias_symbols:
            gene.alias_symbols = ",".join(
                hgnc_id_to_alias_symbols[gene.hgnc_id]
            )
        else:
            gene.alias_symbols = None

        if gene.hgnc_id in hgnc_id_to_previous_symbols:
            gene.previous_symbols = ",".join(
                hgnc_id_to_previous_symbols[gene.hgnc_id]
            )
        else:
            gene.previous_symbols = None

        gene.save()

    # hgnc id : refseq
    mane_data: dict[str, str] = {}

    with open(mane_file, "r") as f:
        for row in csv.DictReader(f, delimiter=","):
            if (
                "Gene" not in row
                or "MANE TYPE" not in row
                or "RefSeq StableID GRCh38 / GRCh37" not in row
            ):
                raise ValueError(
                    "Check MANE file columns headers. Error with MANE file"
                )

            gene_symbol = row["Gene"]
            mane_type = row["MANE TYPE"]
            refseq = row["RefSeq StableID GRCh38 / GRCh37"]

            if mane_type == "MANE SELECT":
                hgnc_id = hgnc_symbols_to_hgnc_id.get(gene_symbol)
                if hgnc_id:
                    mane_data[hgnc_id] = refseq
                else:
                    print(f"Could not find hgnc id for {gene_symbol}")

    gff: dict[str, list] = collections.defaultdict(list)

    with open(gff_file, "r") as f:
        for row in csv.DictReader(
            f,
            delimiter="\t",
            fieldnames=[
                "chrome",
                "start",
                "end",
                "hgnc",
                "transcript",
                "exon",
            ],
        ):
            if row["transcript"].strip() not in gff[row["hgnc"].strip()]:
                gff[row["hgnc"].strip()].append(row["transcript"].strip())

    # two HGMD database tables
    gene2refseq_hgmd: dict[str, list] = collections.defaultdict(list)

    # key = hgnc id (number only)
    markname_hgmd: dict[str, list] = collections.defaultdict(list)

    with open(g2refseq_file, "r") as f:
        for row in csv.DictReader(f, delimiter=","):
            if (
                "hgmdID" not in row
                or "refcore" not in row
                or "refversion" not in row
            ):
                raise ValueError(
                    "Check gene2refseq columns headers. Error with gene2refseq file"
                )

            gene2refseq_hgmd[row["hgmdID"].strip()].append(
                [row["refcore"], row["refversion"]]
            )

    with open(markname_file, "r") as f:
        for row in csv.DictReader(f, delimiter=","):
            if "hgncID" not in row:
                raise ValueError(
                    "Check markname columns headers. Error with markname file"
                )
            markname_hgmd[row["hgncID"].strip()].append(row)

    gene_clinical_transcipt: dict[str, str] = {}
    gene_non_clinical_transcripts: dict[str, list] = collections.defaultdict(
        list
    )

    all_errors = []

    for hgnc_id, transcripts in gff.items():
        for tx in transcripts:
            if hgnc_id in gene_clinical_transcipt:
                # a transcript has been assigned either MANE or HGMD
                gene_non_clinical_transcripts[hgnc_id].append(tx)
                continue

            # comparing just the base, not version
            tx_base, _ = tx.split(".")

            if hgnc_id in mane_data:
                # MANE transcript search
                mane_tx = mane_data[hgnc_id]

                mane_base, _ = mane_tx.split(".")

                if tx_base == mane_base:
                    gene_clinical_transcipt[hgnc_id] = [tx, "MANE"]
                else:
                    gene_non_clinical_transcripts[hgnc_id].append(tx)

            else:
                # HGMD database transcript search
                shortened_hgnc_id = hgnc_id[5:]
                # get transcript from HGMD
                if shortened_hgnc_id not in markname_hgmd:
                    all_errors.append(f"{hgnc_id} not found in HGMD table")
                    gene_non_clinical_transcripts[hgnc_id].append(tx)
                    continue

                if len(markname_hgmd[shortened_hgnc_id]) > 2:
                    all_errors.append(
                        f"{hgnc_id} have two entries in markname table."
                    )
                    gene_non_clinical_transcripts[hgnc_id].append(tx)
                    continue

                markname_data = markname_hgmd[shortened_hgnc_id][0]
                markname_gene_id = markname_data.get("gene_id").strip()

                if not markname_gene_id:
                    all_errors.append(
                        f"{hgnc_id} has no gene_id in markname table"
                    )
                    gene_non_clinical_transcripts[hgnc_id].append(tx)
                    continue

                if markname_gene_id not in gene2refseq_hgmd:
                    all_errors.append(
                        f"{hgnc_id} with gene id {markname_gene_id} not in gene2refseq table"
                    )
                    gene_non_clinical_transcripts[hgnc_id].append(tx)
                    continue

                gene2refseq_data = gene2refseq_hgmd[markname_gene_id]

                if len(gene2refseq_data) > 2:
                    all_errors.append(
                        f'{hgnc_id} have the following transcripts in HGMD database: {",".join(gene2refseq_hgmd)}'
                    )
                    gene_non_clinical_transcripts[hgnc_id].append(tx)
                    continue

                else:
                    hgmd_base, _ = gene2refseq_data[0]

                    if tx_base == hgmd_base:
                        gene_clinical_transcipt[hgnc_id] = [tx, "HGMD"]
                    else:
                        gene_non_clinical_transcripts[hgnc_id].append(tx)

    for hgnc_id, transcript_source in gene_clinical_transcipt.items():
        hgnc, _ = Gene.objects.get_or_create(hgnc_id=hgnc_id)

        transcript, source = transcript_source
        Transcript.objects.get_or_create(
            transcript=transcript, source=source, gene_id=hgnc.id
        )

    for hgnc_id, transcripts in gene_non_clinical_transcripts.items():
        hgnc, _ = Gene.objects.get_or_create(hgnc_id=hgnc_id)

        for tx in transcripts:
            Transcript.objects.get_or_create(
                transcript=tx, source=None, gene_id=hgnc.id
            )

    if write_error_log:
        print(f"Writing error log to {error_log}")
        with open(error_log, "w") as f:
            for row in all_errors:
                f.write(f"{row}\n")
