from django.test import TestCase

from requests_app.models import (
    Transcript,
    TranscriptRelease,
    TranscriptSource,
    Gene,
    TranscriptReleaseTranscript,
    ReferenceGenome,
)
from tests.tests_requests_app.test_management.test_commands.test_insert_panel.test_insert_gene import (
    len_check_wrapper,
    value_check_wrapper,
)
from requests_app.management.commands._parse_transcript import (
    _add_transcript_categorisation_to_db,
)


class TestTranscriptAdded_FromScratch(TestCase):
    def setUp(self) -> None:
        gene = Gene(hgnc_id="HGNC:1", gene_symbol="Test", alias_symbols=None)
        gene.save()

        select = TranscriptSource.objects.create(source="MANE Select")
        plus = TranscriptSource.objects.create(source="MANE Plus Clinical")
        hgmd = TranscriptSource.objects.create(source="HGMD")

        ref_genome = ReferenceGenome.objects.create(reference_genome="GRCh37")

        self.tx = Transcript.objects.create(
            transcript="NM001.4", gene=gene, reference_genome=ref_genome
        )

        self.select_release = TranscriptRelease.objects.create(
            source=select,
            external_release_version="version_3",
            reference_genome=ref_genome,
        )

        self.plus_release = TranscriptRelease.objects.create(
            source=plus,
            external_release_version="version_3",
            reference_genome=ref_genome,
        )

        self.hgmd_release = TranscriptRelease.objects.create(
            source=hgmd, external_release_version="v2", reference_genome=ref_genome
        )

    def test_new_transcript(self):
        """
        CASE: A transcript is being linked to releases for the first time
        EXPECT: Link to be created to 3 releases, each with info about clinical and match status
        """
        err = []  # list of errors to be reported at the end

        input_mane_select = {
            "clinical": True,
            "match_base": True,
            "match_version": False,
        }
        input_mane_plus_clinical = {
            "clinical": None,
            "match_base": None,
            "match_version": None,
        }
        input_hgmd = {"clinical": None, "match_base": None, "match_version": None}

        input_data = {
            self.select_release: input_mane_select,
            self.plus_release: input_mane_plus_clinical,
            self.hgmd_release: input_hgmd,
        }

        _add_transcript_categorisation_to_db(self.tx, input_data)

        tx_link = TranscriptReleaseTranscript.objects.all()
        err += len_check_wrapper(tx_link, "link", 3)
        err += value_check_wrapper(tx_link[0].default_clinical, "clinical", True)
        err += value_check_wrapper(tx_link[0].match_base, "base match", True)
        err += value_check_wrapper(tx_link[0].match_version, "version match", False)
        err += value_check_wrapper(tx_link[1].default_clinical, "clinical", None)
        err += value_check_wrapper(tx_link[1].match_base, "base match", None)
        err += value_check_wrapper(tx_link[1].match_version, "version match", None)
        err += value_check_wrapper(tx_link[2].default_clinical, "clinical", None)
        err += value_check_wrapper(tx_link[2].match_base, "base match", None)
        err += value_check_wrapper(tx_link[2].match_version, "version match", None)

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

        ref_genome = ReferenceGenome.objects.create(reference_genome="GRCh37")

        self.tx = Transcript.objects.create(
            transcript="NM001.4", gene=gene, reference_genome=ref_genome
        )

        self.select_old = TranscriptRelease.objects.create(
            source=select,
            external_release_version="version_3",
            reference_genome=ref_genome,
        )

        self.plus_old = TranscriptRelease.objects.create(
            source=plus,
            external_release_version="version_3",
            reference_genome=ref_genome,
        )

        self.hgmd_old = TranscriptRelease.objects.create(
            source=hgmd, external_release_version="v2", reference_genome=ref_genome
        )

        self.select_new = TranscriptRelease.objects.create(
            source=select,
            external_release_version="version_4",
            reference_genome=ref_genome,
        )

        self.plus_new = TranscriptRelease.objects.create(
            source=plus,
            external_release_version="version_4",
            reference_genome=ref_genome,
        )

        self.hgmd_new = TranscriptRelease.objects.create(
            source=hgmd, external_release_version="v3", reference_genome=ref_genome
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

        input_mane_select = {
            "clinical": True,
            "match_base": True,
            "match_version": False,
        }
        input_mane_plus_clinical = {
            "clinical": None,
            "match_base": None,
            "match_version": None,
        }
        input_hgmd = {"clinical": None, "match_base": None, "match_version": None}

        input_data = {
            self.select_new: input_mane_select,
            self.plus_new: input_mane_plus_clinical,
            self.hgmd_new: input_hgmd,
        }

        _add_transcript_categorisation_to_db(self.tx, input_data)

        tx_link = TranscriptReleaseTranscript.objects.all()
        err += len_check_wrapper(tx_link, "link", 6)

        # see if some of the new info is in there
        err += value_check_wrapper(tx_link[3].release, "select new", self.select_new)
        err += value_check_wrapper(tx_link[3].default_clinical, "clinical", True)
        err += value_check_wrapper(tx_link[3].match_base, "base match", True)
        err += value_check_wrapper(tx_link[3].match_version, "version match", False)

        errors = ", ".join(err)
        assert not errors, errors
