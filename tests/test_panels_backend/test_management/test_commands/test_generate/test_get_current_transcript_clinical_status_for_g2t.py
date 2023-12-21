from django.test import TestCase

from panels_backend.models import (
    ReferenceGenome,
    Gene,
    Transcript,
    TranscriptRelease,
    TranscriptReleaseTranscript,
    TranscriptSource,
)
from panels_backend.management.commands.generate import Command


class TestCurrentTranscript_ManeSelectOnly(TestCase):
    """
    Cases where MANE Select calls a transcript 'clinical'
    """

    def setUp(self) -> None:
        self.ref_genome = ReferenceGenome.objects.create(reference_genome="GRCh38")

        self.gene = Gene.objects.create(
            hgnc_id="HGNC:987", gene_symbol="YFG1", alias_symbols=None
        )

        self.transcript = Transcript.objects.create(
            transcript="NM001",
            gene_id=self.gene.pk,
            reference_genome_id=self.ref_genome.id,
        )

        self.mane_select_source = TranscriptSource.objects.create(source="MANE Select")
        self.mane_plus_source = TranscriptSource.objects.create(
            source="MANE Plus Clinical"
        )
        self.hgmd_source = TranscriptSource.objects.create(source="HGMD")

        self.mane_select_rel = TranscriptRelease.objects.create(
            release="5",
            reference_genome_id=self.ref_genome.id,
            source_id=self.mane_select_source.id,
        )
        self.mane_plus_rel = TranscriptRelease.objects.create(
            release="5",
            reference_genome_id=self.ref_genome.id,
            source_id=self.mane_plus_source.id,
        )
        self.hgmd_rel = TranscriptRelease.objects.create(
            release="7",
            reference_genome_id=self.ref_genome.id,
            source_id=self.hgmd_source.id,
        )

        self.mane_select_link = TranscriptReleaseTranscript.objects.create(
            match_version=True,
            match_base=False,
            default_clinical=True,
            release_id=self.mane_select_rel.id,
            transcript_id=self.transcript.id,
        )

    def test_mane_select_is_clinical_other_sources_dont_exist(self):
        """
        CASE: For a given test transcript, the latest MANE Select release calls it clinical,
        while data from other releases isn't
        EXPECT: Return True, for clinical
        """
        cmd = Command()
        clinical = cmd.get_current_transcript_clinical_status_for_g2t(
            self.transcript, self.mane_select_rel, self.mane_plus_rel, self.hgmd_rel
        )
        assert clinical

    def test_mane_select_is_clinical_other_sources_arent(self):
        """
        CASE: For a given test transcript, the latest MANE Select release calls it clinical,
        while data from other releases are not-clinical
        EXPECT: Return True, for clinical
        """
        self.mane_plus_link = TranscriptReleaseTranscript.objects.create(
            match_version=False,
            match_base=False,
            default_clinical=False,
            release_id=self.mane_plus_rel.id,
            transcript_id=self.transcript.id,
        )
        self.hgmd_link = TranscriptReleaseTranscript.objects.create(
            match_version=False,
            match_base=False,
            default_clinical=False,
            release_id=self.hgmd_rel.id,
            transcript_id=self.transcript.id,
        )
        cmd = Command()
        clinical = cmd.get_current_transcript_clinical_status_for_g2t(
            self.transcript, self.mane_select_rel, self.mane_plus_rel, self.hgmd_rel
        )
        assert clinical


class TestCurrentTranscript_NoLinks(TestCase):
    """
    Case where a transcript isn't present in any transcript source releases
    """

    def setUp(self) -> None:
        self.ref_genome = ReferenceGenome.objects.create(reference_genome="GRCh38")

        self.gene = Gene.objects.create(
            hgnc_id="HGNC:987", gene_symbol="YFG1", alias_symbols=None
        )

        self.transcript = Transcript.objects.create(
            transcript="NM001",
            gene_id=self.gene.pk,
            reference_genome_id=self.ref_genome.id,
        )

        self.mane_select_source = TranscriptSource.objects.create(source="MANE Select")
        self.mane_plus_source = TranscriptSource.objects.create(
            source="MANE Plus Clinical"
        )
        self.hgmd_source = TranscriptSource.objects.create(source="HGMD")

        self.mane_select_rel = TranscriptRelease.objects.create(
            release="5",
            reference_genome_id=self.ref_genome.id,
            source_id=self.mane_select_source.id,
        )
        self.mane_plus_rel = TranscriptRelease.objects.create(
            release="5",
            reference_genome_id=self.ref_genome.id,
            source_id=self.mane_plus_source.id,
        )
        self.hgmd_rel = TranscriptRelease.objects.create(
            release="7",
            reference_genome_id=self.ref_genome.id,
            source_id=self.hgmd_source.id,
        )

    def test_no_transcript_data(self):
        """
        CASE: A transcript isn't present in the most recent versions of sources
        EXPECT: Return None for clinical
        """
        cmd = Command()
        clinical = cmd.get_current_transcript_clinical_status_for_g2t(
            self.transcript, self.mane_select_rel, self.mane_plus_rel, self.hgmd_rel
        )
        assert clinical == None
