from typing import Any
from django.test import TestCase

import numpy as np

from requests_app.models import (
    HgncRelease,
    GffRelease,
    TranscriptRelease,
    TranscriptSource,
    ReferenceGenome,
)
from requests_app.management.commands.history import History
from requests_app.management.commands._parse_transcript import (
    _check_for_transcript_seeding_version_regression,
)


class TestCheckRegressions_OldHgncRelease(TestCase):
    """
    Check errors are thrown if a HGNC release
    provided by a user, is too old
    """

    def setUp(self) -> None:
        # set up TranscriptSources and ref genome
        self.hgmd_source = TranscriptSource.objects.create(source="HGMD")
        self.mane_select_source = TranscriptSource.objects.create(source="MANE Select")
        self.mane_plus_source = TranscriptSource.objects.create(
            source="MANE Plus Clinical"
        )

        self.reference_genome = ReferenceGenome.objects.create(
            reference_genome="GRCh37"
        )

        # pre-populate releases
        self.hgnc = HgncRelease.objects.create(hgnc_release="2")
        self.gff = GffRelease.objects.create(
            gff_release="1.0", reference_genome=self.reference_genome
        )
        self.gff_2 = GffRelease.objects.create(
            gff_release="0.5", reference_genome=self.reference_genome
        )
        self.mane_select = TranscriptRelease.objects.create(
            release="2",
            source=self.mane_select_source,
            reference_genome=self.reference_genome,
        )
        self.mane_plus = TranscriptRelease.objects.create(
            release="2",
            source=self.mane_plus_source,
            reference_genome=self.reference_genome,
        )
        self.hgmd = TranscriptRelease.objects.create(
            release="2", source=self.hgmd_source, reference_genome=self.reference_genome
        )

    def test_one_old_release(self):
        """
        CASE: All user-provided releases are newer/same age as in db, EXCEPT the HGNC release
        is too old.
        EXPECT: Exception raised with an error for the HGNC release
        """
        new_hgnc = 1
        new_gff = 1.0
        new_mane = 2
        new_hgmd = 2.1

        expected_err = (
            "Abandoning input because: hgnc release is a lower version than 2"
        )
        with self.assertRaises(ValueError) as err:
            _check_for_transcript_seeding_version_regression(
                new_hgnc, new_gff, new_mane, new_hgmd, self.reference_genome
            )
        self.assertEquals(str(err.exception), expected_err)

    def test_multiple_old_releases(self):
        """
        CASE: All user-provided releases are newer/same age as in db, EXCEPT for two which
        are too old
        EXPECT: Exception raised with an error for the affected releases only.
        """
        new_hgnc = "1"  # too old
        new_gff = "1.0"
        new_mane = "2"
        new_hgmd = "1.9.0"  # too old, uses subversioning

        expected_err = "Abandoning input because: hgnc release is a lower version than 2; gff release is a lower version than 1.0"
        with self.assertRaises(ValueError) as err:
            _check_for_transcript_seeding_version_regression(
                new_hgnc, new_gff, new_mane, new_hgmd, self.reference_genome
            )
        self.assertEquals(str(err.exception), expected_err)


class TestCheckRegressions_NoReleasesYet(TestCase):
    """
    Check versions are accepted if the database starts empty
    """

    def setUp(self) -> None:
        self.reference_genome = ReferenceGenome.objects.create(
            reference_genome="GRCh38"
        )

    def test_fresh_db(self):
        """
        CASE: No releases are in the db yet.
        EXPECT: Versions all accepted as there are no others to compare against.
        No error should be raised.
        """
        new_hgnc = "1"
        new_gff = "1.0"
        new_mane = "2"
        new_hgmd = "1.9.0"

        _check_for_transcript_seeding_version_regression(
            new_hgnc, new_gff, new_mane, new_hgmd, self.reference_genome
        )