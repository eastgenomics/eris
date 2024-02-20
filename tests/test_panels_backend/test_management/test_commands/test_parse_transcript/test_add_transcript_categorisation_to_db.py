from django.test import TestCase

from panels_backend.models import (
    Transcript,
    TranscriptRelease,
    TranscriptSource,
    Gene,
    TranscriptReleaseTranscript,
    ReferenceGenome,
)
from tests.test_panels_backend.test_management.test_commands.test_insert_panel.test_insert_gene import (
    len_check_wrapper,
    value_check_wrapper,
)
from panels_backend.management.commands._parse_transcript import (
    _add_transcript_categorisation_to_db,
)


class TestTranscriptAdded_FromScratch(TestCase):
    def setUp(self) -> None:
        gene = Gene(hgnc_id="HGNC:1", gene_symbol="Test", alias_symbols=None)
        gene.save()

        select = TranscriptSource.objects.create(source="MANE Select")
        plus = TranscriptSource.objects.create(source="MANE Plus Clinical")
        hgmd = TranscriptSource.objects.create(source="HGMD")

        ref_genome = ReferenceGenome.objects.create(name="GRCh37")

        self.tx = Transcript.objects.create(
            transcript="NM001.4", gene=gene, reference_genome=ref_genome
        )

        self.select_release = TranscriptRelease.objects.create(
            source=select,
            release="version_3",
            reference_genome=ref_genome,
        )

        self.plus_release = TranscriptRelease.objects.create(
            source=plus,
            release="version_3",
            reference_genome=ref_genome,
        )

        self.hgmd_release = TranscriptRelease.objects.create(
            source=hgmd, release="v2", reference_genome=ref_genome
        )

    def test_new_transcript(self):
        """
        CASE: A transcript is being linked to releases for the first time
        EXPECT: Link to be created to 3 releases, each with info about clinical and match status
        """
        err = []  # list of errors to be reported at the end

        input_data = [
            {
                "transcript": self.tx,
                "release": self.select_release,
                "clinical": True,
                "match_base": True,
                "match_version": False,
            },
            {
                "transcript": self.tx,
                "release": self.plus_release,
                "clinical": None,
                "match_base": None,
                "match_version": None,
            },
            {
                "transcript": self.tx,
                "release": self.hgmd_release,
                "clinical": None,
                "match_base": None,
                "match_version": None,
            },
        ]

        _add_transcript_categorisation_to_db(input_data)

        tx_link = TranscriptReleaseTranscript.objects.all()
        err += len_check_wrapper(tx_link, "link", 3)
        err += value_check_wrapper(
            tx_link[0].default_clinical, "clinical", True
        )
        err += value_check_wrapper(tx_link[0].match_base, "base match", True)
        err += value_check_wrapper(
            tx_link[0].match_version, "version match", False
        )
        err += value_check_wrapper(
            tx_link[1].default_clinical, "clinical", None
        )
        err += value_check_wrapper(tx_link[1].match_base, "base match", None)
        err += value_check_wrapper(
            tx_link[1].match_version, "version match", None
        )
        err += value_check_wrapper(
            tx_link[2].default_clinical, "clinical", None
        )
        err += value_check_wrapper(tx_link[2].match_base, "base match", None)
        err += value_check_wrapper(
            tx_link[2].match_version, "version match", None
        )

        errors = "".join(err)
        assert not errors, errors


class TestTranscriptAdded_PreexistingReleases(TestCase):
    """
    CASE: A transcript is being linked to releases for the second time.
    Set up by making the old transcript-release links
    """

    def setUp(self) -> None:
        gene = Gene(hgnc_id="HGNC:1", gene_symbol="Test", alias_symbols=None)
        gene.save()

        select = TranscriptSource.objects.create(source="MANE Select")
        plus = TranscriptSource.objects.create(source="MANE Plus Clinical")
        hgmd = TranscriptSource.objects.create(source="HGMD")

        ref_genome = ReferenceGenome.objects.create(name="GRCh37")

        self.tx = Transcript.objects.create(
            transcript="NM001.4", gene=gene, reference_genome=ref_genome
        )

        self.select_old = TranscriptRelease.objects.create(
            source=select,
            release="version_3",
            reference_genome=ref_genome,
        )

        self.plus_old = TranscriptRelease.objects.create(
            source=plus,
            release="version_3",
            reference_genome=ref_genome,
        )

        self.hgmd_old = TranscriptRelease.objects.create(
            source=hgmd, release="v2", reference_genome=ref_genome
        )

        self.select_new = TranscriptRelease.objects.create(
            source=select,
            release="version_4",
            reference_genome=ref_genome,
        )

        self.plus_new = TranscriptRelease.objects.create(
            source=plus,
            release="version_4",
            reference_genome=ref_genome,
        )

        self.hgmd_new = TranscriptRelease.objects.create(
            source=hgmd, release="v3", reference_genome=ref_genome
        )

        self.select_old_link = TranscriptReleaseTranscript.objects.create(
            transcript=self.tx,
            release=self.select_old,
            match_version=True,
            match_base=True,
            default_clinical=False,
        )

        self.plus_old_link = TranscriptReleaseTranscript.objects.create(
            transcript=self.tx,
            release=self.plus_old,
            match_version=True,
            match_base=True,
            default_clinical=False,
        )

        self.hgmd_old_link = TranscriptReleaseTranscript.objects.create(
            transcript=self.tx,
            release=self.hgmd_old,
            match_version=True,
            match_base=True,
            default_clinical=False,
        )

    def test_transcript_in_earlier_release(self):
        """
        CASE: A transcript is being linked to releases for the second time.
        EXPECT: Link to be created to 6 releases (3 older 3 newer), each with
        info about clinical
        and match status. Old links should still exist unchanged.
        """
        err = []  # list of errors to be reported at the end

        input_data = [
            {
                "transcript": self.tx,
                "release": self.select_new,
                "clinical": True,
                "match_base": True,
                "match_version": False,
            },
            {
                "transcript": self.tx,
                "release": self.plus_new,
                "clinical": None,
                "match_base": None,
                "match_version": None,
            },
            {
                "transcript": self.tx,
                "release": self.hgmd_new,
                "clinical": None,
                "match_base": None,
                "match_version": None,
            },
        ]

        _add_transcript_categorisation_to_db(input_data)

        tx_link = TranscriptReleaseTranscript.objects.all()
        err += len_check_wrapper(tx_link, "link", 6)

        # see if some of the new info is in there
        err += value_check_wrapper(
            tx_link[3].release, "select new", self.select_new
        )
        err += value_check_wrapper(
            tx_link[3].default_clinical, "clinical", True
        )
        err += value_check_wrapper(tx_link[3].match_base, "base match", True)
        err += value_check_wrapper(
            tx_link[3].match_version, "version match", False
        )

        errors = ", ".join(err)
        assert not errors, errors
