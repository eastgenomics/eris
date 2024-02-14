from django.test import TestCase


from panels_backend.models import (
    TranscriptSource,
    TranscriptFile,
    TranscriptRelease,
    TranscriptReleaseTranscriptFile,
    ReferenceGenome,
)
from panels_backend.management.commands._parse_transcript import (
    _add_transcript_release_info_to_db,
)
from tests.test_panels_backend.test_management.test_commands.test_insert_panel.test_insert_gene import (
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
        err += value_check_wrapper(release.release, "release", "v1.2.3")
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


class TestAddTranscriptRelease_ErrorsOnVersionRepeatsWithDifferentFiles(
    TestCase
):
    """
    CASE: An identical transcript release already exists in the DB - this release has been linked to file id 123
    EXPECT: A ValueError should be raised!
    """

    def setUp(self) -> None:
        self.reference_genome = ReferenceGenome.objects.create(name="GRCh37")
        self.source = TranscriptSource.objects.create(source="HGMD")
        self.release = TranscriptRelease.objects.create(
            source=self.source,
            release="v1.0.5",
            reference_genome=self.reference_genome,
        )

        self.tf = TranscriptFile.objects.create(
            file_id="file-123", file_type="hgmd_markname"
        )

        TranscriptReleaseTranscriptFile.objects.create(
            transcript_release=self.release, transcript_file=self.tf
        )

    def test_same_release_different_file_id(self):
        """
        Case: db already have a release & source & version for a specific file type & file-id
        A new seed is uploaded but with a different file-id for the same file type & release version
        e.g.
        HGMD v1.0.5 has file-id 123, GRch37, markname
        but user seed a new HGMD v1.0.5 with "file-id 124", GRch37, markname

        Expect: ValueError to be raised because the file-id of a previous release version is already in the database
        If the user wants to upload a new release version, they should use a new DNAnexus file-id
        """

        source = "HGMD"
        version = "v1.0.5"
        ref_genome = self.reference_genome
        files = {"hgmd_markname": "file-124"}  # different file-id

        with self.assertRaises(ValueError):
            _add_transcript_release_info_to_db(
                source, version, ref_genome, files
            )


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
            release="v1.0.5",
            reference_genome=self.reference_genome,
        )
        self.file_one = TranscriptFile.objects.create(
            file_id="123", file_type="test"
        )
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

        result = _add_transcript_release_info_to_db(
            source, version, ref_genome, data
        )
        self.assertEqual(result, self.release)

        files = TranscriptFile.objects.all()
        assert len(files) == 1
        self.assertEqual(files[0], self.file_one)
