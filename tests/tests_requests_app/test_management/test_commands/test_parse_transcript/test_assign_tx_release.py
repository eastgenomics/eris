from django.test import TestCase


from requests_app.models import \
    Gene, Transcript, TranscriptSource, TranscriptRelease,\
    TranscriptReleaseFile

from requests_app.management.commands._parse_transcript import \
    _assign_tx_release
from ..test_insert_panel.test_insert_gene import len_check_wrapper, value_check_wrapper


class TestAssignTxRelease_NewRelease(TestCase):
    """
    Tests cases where a transcript release is novel to the database,
    so that it is created fresh in the database, and has files linked to it.
    Check that all the files are linked correctly.
    """
    def setUp(self) -> None:
        self.release = "1.1.5"
        self.tx_mane_source = TranscriptSource(
            source="MANE"
        )
        self.tx_mane_source.save()

        self.tx_ref_genome = "37"
    
    def test_novel_release_mane(self):
        """
        Check that typical files for a MANE
        release are successfully added.
        Need to make a TranscriptSource first.
        """
        err = []

        files = {"file-1234": "mane_grch37",
                 "file-5678": "mane_hrch38_ftp"}

        tx_release = _assign_tx_release(self.release, self.tx_mane_source, 
                                        self.tx_ref_genome, files)

        # check the new release is made in TranscriptRelease
        transcript_release = TranscriptRelease.objects.all()

        assert len(transcript_release) == 1
        err += value_check_wrapper(transcript_release[0].source.source, "release source",
                                   "MANE")
        err += value_check_wrapper(transcript_release[0].external_release_version,
                                   "ext release version", "1.1.5")

        # check tx release supporting files are made
        transcript_release_file = TranscriptReleaseFile.objects.all()

        assert len(transcript_release_file) == 2
        first_file = transcript_release_file[0]
        second_file = transcript_release_file[1]
        err += value_check_wrapper(first_file.file_id, "file id", "file-1234")
        err += value_check_wrapper(first_file.file_type, "file type", "mane_grch37")
        err += value_check_wrapper(second_file.file_id, "file id", "file-5678")
        err += value_check_wrapper(second_file.file_type, "file type", "mane_hrch38_ftp")
        
        # check both files are linked to the correct release!
        err += value_check_wrapper(first_file.transcript_release,
                                   "tx release",
                                   tx_release)
        err += value_check_wrapper(second_file.transcript_release,
                                   "tx release",
                                   tx_release)

        errors = "; ".join(err)
        assert not errors, errors

