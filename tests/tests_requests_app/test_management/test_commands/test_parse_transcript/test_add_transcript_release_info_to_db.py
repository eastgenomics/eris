from django.test import TestCase

import numpy as np

from requests_app.models import TranscriptSource, TranscriptFile, TranscriptRelease, \
    TranscriptReleaseTranscriptFile
from requests_app.management.commands._parse_transcript import \
    _add_transcript_release_info_to_db
from tests.tests_requests_app.test_management.test_commands.test_insert_panel.test_insert_gene import \
    len_check_wrapper, value_check_wrapper


class TestAddTranscriptRelease_FromScratch(TestCase):
    """
    _add_transcript_release_info_to_db adds transcript sources, releases,
    and supporting file IDs to the database.
    First test if it successfully adds new data to an entirely empty starting db.
    """
    def test_basic_add_transcript_release(self):
        """
        Add to an empty db
        Expect: new transcript source, new release, and a new entry for each file.
        """
        err = []

        source = "MANE Select"
        version = "v1.2.3"
        ref_genome = "37"
        data = {"mane": "file-1357", "another_mane": "file 101010"}

        _add_transcript_release_info_to_db(source, version, ref_genome,
                                           data)
        
        sources = TranscriptSource.objects.all()
        files = TranscriptFile.objects.all()
        releases = TranscriptRelease.objects.all()
        release_file_links = TranscriptReleaseTranscriptFile.objects.all()

        # check lengths
        err += len_check_wrapper(sources, "sources", 1)
        err += len_check_wrapper(files, "files", 1)
        err += len_check_wrapper(releases, "releases", 1)
        err += release_file_links(release_file_links, "links", 1)


        errors = "".join(err)
        assert not errors, errors

