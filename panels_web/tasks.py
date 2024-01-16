from celery import shared_task


from panels_backend.management.commands.seed import (
    validate_ext_ids,
    validate_release_versions,
)
from panels_backend.management.commands._parse_transcript import seed_transcripts
from panels_backend.models import (
    ReferenceGenome,
    TranscriptRelease,
    GffRelease,
    HgncRelease,
)
import pandas as pd
import io
import base64
from panels_backend.management.commands._parse_transcript import (
    parse_reference_genome,
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
) -> None:
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
) -> None:
    """
    Sub-function to gather all required inputs from web front-end and
    call seed_functions (panels_backend/management/commands/_parse_transcript.py)
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
