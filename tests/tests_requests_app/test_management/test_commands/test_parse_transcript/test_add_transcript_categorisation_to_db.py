from django.test import TestCase

from requests_app.models import Transcript, TranscriptRelease,\
    TranscriptSource, Gene, TranscriptReleaseTranscript
from tests.tests_requests_app.test_management.test_commands.test_insert_panel.test_insert_gene import (
    len_check_wrapper,
    value_check_wrapper
    )
from requests_app.management.commands._parse_transcript import \
    _add_transcript_categorisation_to_db


class TestTranscriptAdded_FromScratch(TestCase):
    def test_new_transcript(self):
        """
        CASE: A transcript is being linked to a release for the first time
        EXPECT: Link to be created with info about clinical and match status
        """
        err = []  # list of errors to be reported at the end

        gene = Gene(hgnc_id="HGNC:1",
                    gene_symbol="Test",
                    alias_symbols=None)
        gene.save()
        source = TranscriptSource(source="MANE Select")
        source.save()
        tx = Transcript(transcript="NM001.4",
                        gene=gene,
                        reference_genome="37")
        tx.save()
        release = TranscriptRelease(source=source,
                                    external_release_version="version_3",
                                    reference_genome="37")
        release.save()
        input_mane_select = {"clinical": True,
                             "match_base": True,
                             "match_version": False}
        
        _add_transcript_categorisation_to_db(tx, release, input_mane_select)
        
        tx_link = TranscriptReleaseTranscript.objects.all()
        err += len_check_wrapper(tx_link, "link", 1)
        err += value_check_wrapper(tx_link[0].default_clinical, "clinical", True)
        err += value_check_wrapper(tx_link[0].match_base, "base match", True)
        err += value_check_wrapper(tx_link[0].match_version, "version match", False)

        errors = "".join(err)
        assert not errors, errors
