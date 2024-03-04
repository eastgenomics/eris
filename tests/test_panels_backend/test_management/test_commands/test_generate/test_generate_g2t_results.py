from typing import Any
from django.test import TestCase

from panels_backend.models import (
    ReferenceGenome,
    GffRelease,
    Gene,
    Transcript,
    TranscriptSource,
    TranscriptRelease,
    TranscriptGffRelease,
    TranscriptReleaseTranscript,
)
from panels_backend.management.commands.generate import (
    Command,
)


class TestGenerateG2tResults(TestCase):
    def setUp(self) -> None:
        # make reference genomes
        self.grch37 = ReferenceGenome.objects.create(name="GRCh37")
        self.grch38 = ReferenceGenome.objects.create(name="GRCh38")

        # possible GFF releases
        self.gff_18 = GffRelease.objects.create(
            ensembl_release="18", reference_genome=self.grch37
        )

        self.gff_19 = GffRelease.objects.create(
            ensembl_release="19", reference_genome=self.grch37
        )

        # transcript sources and releases
        self.mane_select = TranscriptSource.objects.create(
            source="MANE Select"
        )
        self.mane_plus_clinical = TranscriptSource.objects.create(
            source="MANE Plus Clinical"
        )
        self.hgmd = TranscriptSource.objects.create(source="HGMD")

        self.mane_select_release = TranscriptRelease.objects.create(
            source=self.mane_select,
            release="1.3",
            reference_genome=self.grch37,
        )
        self.mane_plus_clin_release = TranscriptRelease.objects.create(
            source=self.mane_plus_clinical,
            release="1.3",
            reference_genome=self.grch37,
        )
        self.hgmd_clin_release = TranscriptRelease.objects.create(
            source=self.hgmd, release="2.2", reference_genome=self.grch37
        )

        # make a bunch of genes, each with some transcripts
        self.gene_1 = Gene.objects.create(
            hgnc_id="HGNC:3054", gene_symbol="ASG1"
        )
        self.tx_1_1 = Transcript.objects.create(
            transcript="NM012.5",
            gene=self.gene_1,
            reference_genome=self.grch37,
        )
        self.tx_1_2 = Transcript.objects.create(
            transcript="NM1056.3",
            gene=self.gene_1,
            reference_genome=self.grch37,
        )

        self.gene_2 = Gene.objects.create(
            hgnc_id="HGNC:947", gene_symbol="BSG1"
        )
        self.tx_2_1 = Transcript.objects.create(
            transcript="NM4045.5",
            gene=self.gene_2,
            reference_genome=self.grch37,
        )
        self.tx_2_2 = Transcript.objects.create(
            transcript="NM1058.2",
            gene=self.gene_2,
            reference_genome=self.grch37,
        )

        self.gene_3 = Gene.objects.create(
            hgnc_id="HGNC:12", gene_symbol="CSG1"
        )
        self.tx_3_1 = Transcript.objects.create(
            transcript="NM00092.1",
            gene=self.gene_3,
            reference_genome=self.grch37,
        )
        self.tx_3_2 = Transcript.objects.create(
            transcript="NM10.2", gene=self.gene_3, reference_genome=self.grch37
        )

        # transcripts also belong to one or more GFF releases, which
        # determines whether VEP can annotate with them

        # TWO of the transcripts aren't linked to our most-recent GFF
        # but are instead linked to the older GFF
        TranscriptGffRelease.objects.create(
            transcript=self.tx_1_2, gff_release=self.gff_18
        )

        TranscriptGffRelease.objects.create(
            transcript=self.tx_3_1, gff_release=self.gff_18
        )

        # ONE of the transcripts is linked to both old and new GFFs
        TranscriptGffRelease.objects.create(
            transcript=self.tx_1_1, gff_release=self.gff_18
        )

        TranscriptGffRelease.objects.create(
            transcript=self.tx_1_1, gff_release=self.gff_19
        )

        # THREE of the transcripts are linked to the new GFF only
        TranscriptGffRelease.objects.create(
            transcript=self.tx_2_1, gff_release=self.gff_19
        )

        TranscriptGffRelease.objects.create(
            transcript=self.tx_2_2, gff_release=self.gff_19
        )

        TranscriptGffRelease.objects.create(
            transcript=self.tx_3_2, gff_release=self.gff_19
        )

        # Finally, give all the transcripts clinical info links
        # tx_1_1 - MANE select
        TranscriptReleaseTranscript.objects.create(
            transcript_id=self.tx_1_1.id,
            release_id=self.mane_select_release.id,
            match_version=True,
            match_base=True,
            default_clinical=True,
        )

        TranscriptReleaseTranscript.objects.create(
            transcript_id=self.tx_1_1.id,
            release_id=self.mane_plus_clin_release.id,
            match_version=None,
            match_base=None,
            default_clinical=None,
        )

        TranscriptReleaseTranscript.objects.create(
            transcript_id=self.tx_1_1.id,
            release_id=self.hgmd_clin_release.id,
            match_version=None,
            match_base=None,
            default_clinical=None,
        )

        # tx_1_2 - Mane Plus Clinical
        TranscriptReleaseTranscript.objects.create(
            transcript_id=self.tx_1_2.id,
            release_id=self.mane_select_release.id,
            match_version=None,
            match_base=None,
            default_clinical=None,
        )

        TranscriptReleaseTranscript.objects.create(
            transcript_id=self.tx_1_2.id,
            release_id=self.mane_plus_clin_release.id,
            match_version=False,
            match_base=True,
            default_clinical=True,
        )

        TranscriptReleaseTranscript.objects.create(
            transcript_id=self.tx_1_2.id,
            release_id=self.hgmd_clin_release.id,
            match_version=None,
            match_base=None,
            default_clinical=None,
        )

        # tx_2_1 - has a Select link, but no Plus Clinical
        TranscriptReleaseTranscript.objects.create(
            transcript_id=self.tx_2_1.id,
            release_id=self.mane_select_release.id,
            match_version=False,
            match_base=True,
            default_clinical=True,
        )

        TranscriptReleaseTranscript.objects.create(
            transcript_id=self.tx_2_1.id,
            release_id=self.mane_plus_clin_release.id,
            match_version=None,
            match_base=None,
            default_clinical=None,
        )

        TranscriptReleaseTranscript.objects.create(
            transcript_id=self.tx_2_1.id,
            release_id=self.hgmd_clin_release.id,
            match_version=None,
            match_base=None,
            default_clinical=None,
        )

        # tx_2_2 - not clinical at all
        TranscriptReleaseTranscript.objects.create(
            transcript_id=self.tx_2_2.id,
            release_id=self.mane_select_release.id,
            match_version=None,
            match_base=None,
            default_clinical=None,
        )

        TranscriptReleaseTranscript.objects.create(
            transcript_id=self.tx_2_2.id,
            release_id=self.mane_plus_clin_release.id,
            match_version=None,
            match_base=None,
            default_clinical=None,
        )

        TranscriptReleaseTranscript.objects.create(
            transcript_id=self.tx_2_2.id,
            release_id=self.hgmd_clin_release.id,
            match_version=None,
            match_base=None,
            default_clinical=None,
        )

        # tx_3_1 - not clinical
        TranscriptReleaseTranscript.objects.create(
            transcript_id=self.tx_3_1.id,
            release_id=self.mane_select_release.id,
            match_version=None,
            match_base=None,
            default_clinical=None,
        )

        TranscriptReleaseTranscript.objects.create(
            transcript_id=self.tx_3_1.id,
            release_id=self.mane_plus_clin_release.id,
            match_version=None,
            match_base=None,
            default_clinical=None,
        )

        TranscriptReleaseTranscript.objects.create(
            transcript_id=self.tx_3_1.id,
            release_id=self.hgmd_clin_release.id,
            match_version=None,
            match_base=None,
            default_clinical=None,
        )

        # tx_3_2 - HGMD
        TranscriptReleaseTranscript.objects.create(
            transcript_id=self.tx_3_2.id,
            release_id=self.mane_select_release.id,
            match_version=None,
            match_base=None,
            default_clinical=None,
        )

        TranscriptReleaseTranscript.objects.create(
            transcript_id=self.tx_3_2.id,
            release_id=self.mane_plus_clin_release.id,
            match_version=None,
            match_base=None,
            default_clinical=None,
        )

        TranscriptReleaseTranscript.objects.create(
            transcript_id=self.tx_3_2.id,
            release_id=self.hgmd_clin_release.id,
            match_version=False,
            match_base=True,
            default_clinical=True,
        )

    def test_retrieve_gff_19_g2t(self):
        """
        CASE: User asks for GFF release 19, GRCh37 g2t file.
        EXPECT: Results contain only GFF-compatible, GRCh37
        transcripts and genes. Some are clinical, some aren't.
        """
        cmd = Command()

        expected = [
            {
                "hgnc_id": "HGNC:3054",
                "transcript": self.tx_1_1.transcript,
                "clinical": "clinical_transcript",
            },
            {
                "hgnc_id": "HGNC:947",
                "transcript": self.tx_2_1.transcript,
                "clinical": "clinical_transcript",
            },
            {
                "hgnc_id": "HGNC:947",
                "transcript": self.tx_2_2.transcript,
                "clinical": "not_clinical_transcript",
            },
            {
                "hgnc_id": "HGNC:12",
                "transcript": self.tx_3_2.transcript,
                "clinical": "clinical_transcript",
            },
        ]

        result = cmd._generate_g2t_results(
            self.grch37,
            self.gff_19,
            self.mane_select_release,
            self.mane_plus_clin_release,
            self.hgmd_clin_release,
        )
        self.assertEqual(expected, result)
