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
        data = {"mane": "file-1357", "another_mane": "file-101010"}

        _add_transcript_release_info_to_db(source, version, ref_genome,
                                           data)
        
        sources = TranscriptSource.objects.all()
        files = TranscriptFile.objects.all()
        releases = TranscriptRelease.objects.all()
        release_file_links = TranscriptReleaseTranscriptFile.objects.all()

        # check lengths
        err += len_check_wrapper(sources, "sources", 1)
        err += len_check_wrapper(files, "files", 2)
        err += len_check_wrapper(releases, "releases", 1)
        err += len_check_wrapper(release_file_links, "links", 2)

        # check contents
        source = sources[0]
        file_1 = files[0]
        file_2 = files[1]
        release = releases[0]
        rel_file_link_1 = release_file_links[0]
        rel_file_link_2 = release_file_links[1]

        err += value_check_wrapper(source.source, "source name", "MANE Select")
        err += value_check_wrapper(file_1.file_id, "file ID 1", "file-1357")
        err += value_check_wrapper(file_2.file_id, "file ID 2", "file-101010")
        err += value_check_wrapper(release.external_release_version, "release",
                                   "v1.2.3")
        err += value_check_wrapper(rel_file_link_1.transcript_release, "release-file link 1", release)
        err += value_check_wrapper(rel_file_link_2.transcript_release, "release-file link 2", release)
        err += value_check_wrapper(rel_file_link_1.transcript_file, "release-file link 1", file_1)
        err += value_check_wrapper(rel_file_link_2.transcript_file, "release-file link 2", file_2)

        errors = "".join(err)
        assert not errors, errors


class TestAddTranscriptRelease_ErrorsOnVersionRepeats(TestCase):
    """
    _add_transcript_release_info_to_db adds transcript sources, releases,
    and supporting file IDs to the database.
    If a transcript release already exists in the DB for the source being
    processed, it should raise a ValueError to block the process.
    """
    # TODO: set this up
    def setUp(self) -> None:
        # TODO: we need a TranscriptRelease already in the db, and a source too
        pass

    def test_quits_if_repeat_external_release_version(self):
        """
        Add to a db with a release already in it
        Expect: throws information ValueError
        """
        err = []

        #TODO: write body of test here

        errors = "".join(err)
        assert not errors, errors
