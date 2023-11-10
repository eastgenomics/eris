from django.test import TestCase

import numpy as np

from requests_app.models import (
    TranscriptSource,
    TranscriptFile,
    TranscriptRelease,
    TranscriptReleaseTranscriptFile,
    ReferenceGenome,
)
from requests_app.management.commands._parse_transcript import (
    _add_transcript_release_info_to_db,
)
from tests.tests_requests_app.test_management.test_commands.test_insert_panel.test_insert_gene import (
    len_check_wrapper,
    value_check_wrapper,
)


class TestAddTranscriptRelease_FromScratch(TestCase):
    """
    _add_transcript_release_info_to_db adds transcript sources, releases,
    and supporting file IDs to the database.
    First test checks if it successfully adds new data to an entirely empty starting db.
    """

    def test_basic_add_transcript_release(self):
        """
        Add to an empty db
        Expect: new transcript source, new release, and a new entry for each file.
        """
        err = []

        source = "MANE Select"
        version = "v1.2.3"
        ref_genome = ReferenceGenome.objects.create(name="GRCh37")

        data = {"mane": "file-1357", "another_mane": "file-101010"}

        _add_transcript_release_info_to_db(source, version, ref_genome, data)

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
        err += value_check_wrapper(
            release.external_release_version, "release", "v1.2.3"
        )
        err += value_check_wrapper(
            rel_file_link_1.transcript_release, "release-file link 1", release
        )
        err += value_check_wrapper(
            rel_file_link_2.transcript_release, "release-file link 2", release
        )
        err += value_check_wrapper(
            rel_file_link_1.transcript_file, "release-file link 1", file_1
        )
        err += value_check_wrapper(
            rel_file_link_2.transcript_file, "release-file link 2", file_2
        )

        errors = "".join(err)
        assert not errors, errors


class TestAddTranscriptRelease_ErrorsOnVersionRepeatsWithDifferentFiles(TestCase):
    """
    _add_transcript_release_info_to_db adds transcript sources, releases,
    and supporting file IDs to the database.
    CASE: An identical transcript release already exists in the DB, but no files are linked
    EXPECT: The old db copy of the release is fetched, and because the new files 'don't match'
    the old missing ones, an error is raised.
    """

    def setUp(self) -> None:
        self.reference_genome = ReferenceGenome.objects.create(name="GRCh37")
        self.source = TranscriptSource.objects.create(source="HGMD")
        self.release = TranscriptRelease.objects.create(
            source=self.source,
            external_release_version="v1.0.5",
            reference_genome=self.reference_genome,
        )

    def test_non_matching_files_throw_errors(self):
        """
        Case: Add to a db with a perfectly-matching release already in it.
        Expect: the old files don't match the newly-uploaded ones - raise an error
        """
        self.maxDiff = None

        source = "HGMD"
        version = "v1.0.5"
        ref_genome = self.reference_genome
        data = {"mane": "file-1357", "another_mane": "file-101010"}

        with self.assertRaisesRegex(
            ValueError,
            "Transcript release HGMD v1.0.5 already exists in db, but the uploaded file file-1357 is"
            " not in the db. Please review. Transcript release HGMD v1.0.5 already exists in db, "
            "but the uploaded file file-101010 is not in the db. Please review.",
        ):
            _add_transcript_release_info_to_db(source, version, ref_genome, data)


class TestAddTranscriptRelease_SameFilesNoProblem(TestCase):
    """
    _add_transcript_release_info_to_db adds transcript sources, releases,
    and supporting file IDs to the database.
    CASE: An identical transcript release already exists in the DB, and the files linked
    are the same too.
    EXPECT: The old db copy of the release is fetched, and because the new files have the
    same IDs as the old one, there isn't an error.
    """

    def setUp(self) -> None:
        self.reference_genome = ReferenceGenome.objects.create(name="GRCh37")
        self.source = TranscriptSource.objects.create(source="HGMD")
        self.release = TranscriptRelease.objects.create(
            source=self.source,
            external_release_version="v1.0.5",
            reference_genome=self.reference_genome,
        )
        self.file_one = TranscriptFile.objects.create(file_id="123", file_type="test")
        self.li = TranscriptReleaseTranscriptFile.objects.create(
            transcript_release=self.release, transcript_file=self.file_one
        )

    def test_external_release_version_fetched(self):
        """
        Add to a db with a perfectly-matching release AND file already in it.
        Expect: get instead of create - the release is returned without issue.
        """
        source = "HGMD"
        version = "v1.0.5"
        ref_genome = self.reference_genome
        data = {"test": "123"}

        result = _add_transcript_release_info_to_db(source, version, ref_genome, data)
        self.assertEqual(result, self.release)

        files = TranscriptFile.objects.all()
        assert len(files) == 1
        self.assertEqual(files[0], self.file_one)


class TestAddTranscriptRelease_CheckNotMissingFiles(TestCase):
    """
    _add_transcript_release_info_to_db adds transcript sources, releases,
    and supporting file IDs to the database.
    CASE: An identical transcript release already exists in the DB, but it has more files linked
     to it that the user isn't currently uploading
    EXPECT: The old db copy of the release is fetched, and because there are fewer files
    being linked than expected, an error is raised.
    """

    def setUp(self) -> None:
        self.reference_genome = ReferenceGenome.objects.create(name="GRCh37")
        self.source = TranscriptSource.objects.create(source="HGMD")
        self.release = TranscriptRelease.objects.create(
            source=self.source,
            external_release_version="v1.0.5",
            reference_genome=self.reference_genome,
        )
        self.file_one = TranscriptFile.objects.create(file_id="123", file_type="test")
        self.link_1 = TranscriptReleaseTranscriptFile.objects.create(
            transcript_release=self.release, transcript_file=self.file_one
        )
        self.file_two = TranscriptFile.objects.create(file_id="456", file_type="test")
        self.link_2 = TranscriptReleaseTranscriptFile.objects.create(
            transcript_release=self.release, transcript_file=self.file_two
        )

    def test_missing_files_throw_errors(self):
        """
        Case: Add to a db with a perfectly-matching release already in it.
        Expect: there are more old files than new ones - throw error
        """
        source = "HGMD"
        version = "v1.0.5"
        ref_genome = self.reference_genome
        data = {"mane": "123"}

        with self.assertRaisesRegex(
            ValueError,
            "Transcript file 456 is linked to the release in the db, but wasn't uploaded. Please review.",
        ):
            _add_transcript_release_info_to_db(source, version, ref_genome, data)
