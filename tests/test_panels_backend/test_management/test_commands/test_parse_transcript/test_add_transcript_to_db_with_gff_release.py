from django.test import TestCase

from panels_backend.models import (
    Gene,
    Transcript,
    GffRelease,
    TranscriptGffRelease,
    TranscriptGffReleaseHistory,
    ReferenceGenome,
)
from panels_backend.management.commands.history import History
from panels_backend.management.commands._parse_transcript import (
    _add_transcript_to_db_with_gff_release,
)
from tests.test_panels_backend.test_management.test_commands.test_insert_panel.test_insert_gene import (
    len_check_wrapper,
    value_check_wrapper,
)


class TestAddTranscriptWithGff_NewTranscript(TestCase):
    """
    Emulate the case where a brand new transcript is being added to
    the database for the first time.
    """

    def setUp(self) -> None:
        self.gene, _ = Gene.objects.get_or_create(
            hgnc_id="HGNC:1034", gene_symbol="ABC1", alias_symbols="GET1,AND1"
        )

        self.transcript_name = "NM04582.5"

        self.ref_genome, _ = ReferenceGenome.objects.get_or_create(name="GRCh37")

        self.gff_release, _ = GffRelease.objects.get_or_create(
            gencode_release="10", reference_genome=self.ref_genome
        )

        self.user = "init_v1_user"

    def test_novel_transcript_links_successfully(self):
        """
        CASE: A new transcript needs adding to the database
        EXPECT: Tx adds, links to currently-provided GFF release, and logs history
        saying this is a brand new transcript with a link.
        """
        err = []

        tx = _add_transcript_to_db_with_gff_release(
            self.gene,
            self.transcript_name,
            self.ref_genome,
            self.gff_release,
            self.user,
        )

        tx = Transcript.objects.all()
        err += len_check_wrapper(tx, "transcripts created", 1)
        err += value_check_wrapper(
            tx[0].transcript, "transcript name", self.transcript_name
        )

        release = GffRelease.objects.all()
        err += len_check_wrapper(release, "releases", 1)
        err += value_check_wrapper(release[0].gencode_release, "release version", "10")

        tx_release = TranscriptGffRelease.objects.all()
        err += len_check_wrapper(tx_release, "tx-release links", 1)
        err += value_check_wrapper(tx_release[0].transcript, "linked tx", tx[0])
        err += value_check_wrapper(
            tx_release[0].gff_release, "linked release", release[0]
        )

        history = TranscriptGffReleaseHistory.objects.all()
        err += len_check_wrapper(history, "history", 1)
        err += value_check_wrapper(
            history[0].transcript_gff, "tx-release", tx_release[0]
        )
        err += value_check_wrapper(
            history[0].note, "tx-release note", History.tx_gff_release_new()
        )

        errors = "; ".join(err)
        assert not errors, errors


class TestAddTranscriptWithGff_ExistingTranscripts(TestCase):
    """
    Emulate cases where a transcript is already in the database,
    but we need to link it to this GFF release for the first time.
    """

    def setUp(self) -> None:
        self.gene, _ = Gene.objects.get_or_create(
            hgnc_id="HGNC:1034", gene_symbol="ABC1", alias_symbols="GET1,AND1"
        )

        self.transcript_name = "NM04582.5"

        self.ref_genome, _ = ReferenceGenome.objects.get_or_create(name="GRCh37")

        self.gff_release, _ = GffRelease.objects.get_or_create(
            gencode_release="10.2", reference_genome=self.ref_genome
        )

        self.transcript, _ = Transcript.objects.get_or_create(
            transcript=self.transcript_name,
            gene=self.gene,
            reference_genome=self.ref_genome,
        )

        self.user = "init_v1_user"

    def test_existing_transcript_links_successfully(self):
        """
        CASE: A transcript already exists in the database, possibly from an earlier GFF release.
        EXPECT: Existing tx links to currently-provided GFF release, and logs history
        saying this is an already-present transcript.
        """
        err = []

        tx = _add_transcript_to_db_with_gff_release(
            self.gene,
            self.transcript_name,
            self.ref_genome,
            self.gff_release,
            self.user,
        )

        tx = Transcript.objects.all()
        err += len_check_wrapper(tx, "transcripts created", 1)
        err += value_check_wrapper(
            tx[0].transcript, "transcript name", self.transcript_name
        )

        release = GffRelease.objects.all()
        err += len_check_wrapper(release, "releases", 1)
        err += value_check_wrapper(release[0].gencode_release, "release version", "10.2")

        tx_release = TranscriptGffRelease.objects.all()
        err += len_check_wrapper(tx_release, "tx-release links", 1)
        err += value_check_wrapper(tx_release[0].transcript, "linked tx", tx[0])
        err += value_check_wrapper(
            tx_release[0].gff_release, "linked release", release[0]
        )

        history = TranscriptGffReleaseHistory.objects.all()
        err += len_check_wrapper(history, "history", 1)
        err += value_check_wrapper(
            history[0].transcript_gff, "tx-release", tx_release[0]
        )
        err += value_check_wrapper(
            history[0].note, "tx-release note", History.tx_gff_release_present()
        )

        errors = "; ".join(err)
        assert not errors, errors

    def test_existing_transcript_existing_gff_link_ignored(self):
        """
        CASE: A transcript already exists in the database, and so does this GFF release.
        EXPECT: Existing tx-gff link is retrieved. History isn't logged as it's redundant.
        """
        err = []

        # make it so that the tx/gff are already linked:
        self.existing_link, _ = TranscriptGffRelease.objects.get_or_create(
            transcript=self.transcript, gff_release=self.gff_release
        )

        _add_transcript_to_db_with_gff_release(
            self.gene,
            self.transcript_name,
            self.ref_genome,
            self.gff_release,
            self.user,
        )

        history = TranscriptGffReleaseHistory.objects.all()
        err += len_check_wrapper(history, "history", 0)

        errors = "; ".join(err)
        assert not errors, errors
