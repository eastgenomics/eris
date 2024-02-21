from typing import Any
from django.test import TestCase

from panels_backend.models import (
    ReferenceGenome,
    GffRelease,
    TranscriptSource,
    TranscriptRelease,
    TranscriptGffRelease,
    Panel,
    PanelGene,
    SuperPanel,
    PanelSuperPanel,
    Gene,
    ClinicalIndication,
    ClinicalIndicationPanel,
    ClinicalIndicationSuperPanel,
    CiPanelTdRelease,
    CiSuperpanelTdRelease,
)
from panels_backend.management.commands.generate import (
    Command,
)


class TestGenerateG2tResults(TestCase):
    def setUp(self) -> None:
        # make reference genomes
        self.grch37 = ReferenceGenome(name="GRCh37")
        self.grch38 = ReferenceGenome(name="GRCh38")

        # possible GFF releases
        self.gff_18 = GffRelease(
            ensembl_release="18", reference_genome=self.grch37
        )

        self.gff_19 = GffRelease(
            ensembl_release="19", reference_genome=self.grch37
        )

        # transcript sources and releases
        self.mane_select = TranscriptSource(source="MANE Select")
        self.mane_plus_clinical = TranscriptSource(source="MANE Plus Clinical")
        self.hgmd = TranscriptSource(source="HGMD")

        self.mane_select_release = TranscriptRelease(
            source=self.mane_select,
            release="1.3",
            reference_genome=self.grch37,
        )
        self.mane_plus_clin_release = TranscriptRelease(
            source=self.mane_plus_clinical,
            release="1.3",
            reference_genome=self.grch37,
        )
        self.hgmd_clin_release = TranscriptRelease(
            source=self.hgmd, release="2.2", reference_genome=self.grch37
        )

        # make a bunch of transcripts, with genes that they belong to

        # transcripts also belong to one or more GFF releases, which
        # determines whether VEP can annotate with them
