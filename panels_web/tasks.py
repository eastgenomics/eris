from celery import shared_task

from panels_backend.management.commands._parse_transcript import seed_transcripts
from panels_backend.models import (
    ReferenceGenome,
    TranscriptRelease,
    GffRelease,
    HgncRelease,
)

from panels_backend.management.commands._parse_transcript import (
    update_existing_gene_metadata,
)


@shared_task(name="updating_gene_metadata")
def call_update_existing_gene_metadata(
    symbol_changed: dict[str, dict[str, str]],
    alias_changed: dict[str, dict[str, str]],
    release_created: bool,
    new_genes: list[dict[str, str | None]],
    hgnc_release_id: HgncRelease,
    unchanged_genes: dict[str, dict[str, str]],
    user: str,
) -> bool:
    """
    Function to call update_existing_gene_metadata function as Celery task

    Params:
    symbol_changed (dict): dictionary containing gene symbols that have been changed
    alias_changed (dict): dictionary containing gene aliases that have been changed
    release_created (bool): boolean indicating whether a new release has been created
    new_genes (list): list of dictionaries containing new gene data
    hgnc_release_id (int): ID of the HGNC release
    unchanged_genes (dict): dictionary containing gene data that has not been changed
    user (str): username of the user who initiated the task
    """
    hgnc_release_model = HgncRelease.objects.get(id=hgnc_release_id)

    update_existing_gene_metadata(
        symbol_changed,
        alias_changed,
        release_created,
        new_genes,
        hgnc_release_model,
        unchanged_genes,
        user,
    )

    return True


@shared_task(name="seed_transcripts")
def call_seed_transcripts_function(
    null_argument: None,
    gff_release_id: int,
    gff: dict[str, list[str]],
    mane_data: list[dict],
    markname_hgmd: dict[str, list[str]],
    gene2refseq_hgmd: dict[str, list[list[str]]],
    reference_genome_id: int,
    mane_select_id: int,
    mane_plus_id: int,
    hgmd_tx_id: int,
    user: str,
) -> bool:
    """
    Sub-function to gather all required inputs from web front-end and
    call seed_functions (panels_backend/management/commands/_parse_transcript.py)
    as Celery backend task

    Params:
    gff_release_id (int): ID of the GFF release
    gff (dict): dictionary containing GFF data
    mane_data (list): list of dictionaries containing MANE data
    markname_hgmd (dict): dictionary containing HGMD data
    gene2refseq_hgmd (dict): dictionary containing gene2refseq data
    reference_genome_id (int): ID of the reference genome
    mane_select_id (int): ID of the MANE Select transcript release
    mane_plus_id (int): ID of the MANE Plus Clinical transcript release
    hgmd_tx_id (int): ID of the HGMD transcript release
    user (str): username of the user who initiated the task
    """

    reference_genome_model = ReferenceGenome.objects.get(id=reference_genome_id)
    mane_select_tx_model = TranscriptRelease.objects.get(id=mane_select_id)
    mane_plus_clinical_tx_model = TranscriptRelease.objects.get(id=mane_plus_id)
    hgmd_tx_model = TranscriptRelease.objects.get(id=hgmd_tx_id)

    gff_release_model = GffRelease.objects.get(id=gff_release_id)

    seed_transcripts(
        gff_release_model,
        gff,
        mane_data,
        markname_hgmd,
        gene2refseq_hgmd,
        reference_genome_model,
        mane_select_tx_model,
        mane_plus_clinical_tx_model,
        hgmd_tx_model,
        user,
    )

    return True
