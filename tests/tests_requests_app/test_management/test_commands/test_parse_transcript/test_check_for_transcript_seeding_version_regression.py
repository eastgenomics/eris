from typing import Any
from django.test import TestCase

import numpy as np

from requests_app.models import (
    HgncRelease,
    GffRelease,
    TranscriptRelease,
    TranscriptSource,
    ReferenceGenome
)
from requests_app.management.commands.history import History
from requests_app.management.commands._parse_transcript import (
    _check_for_transcript_seeding_version_regression,
)
from tests.tests_requests_app.test_management.test_commands.test_insert_panel.test_insert_gene import (
    len_check_wrapper,
    value_check_wrapper,
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
        self.mane_plus_source = TranscriptSource.objects.create(source="MANE Plus Clinical")

        self.reference_genome = ReferenceGenome.objects.create(reference_genome="GRCh37")

        # pre-populate releases
        self.hgnc = HgncRelease.objects.create(hgnc_release="2")
        self.gff = GffRelease.objects.create(gff_release="1.0", reference_genome=self.reference_genome)
        self.mane_select = TranscriptRelease.objects.create(release="2", source=self.mane_select_source,
                                                            reference_genome=self.reference_genome)
        self.mane_plus = TranscriptRelease.objects.create(release="2", source=self.mane_plus_source,
                                                            reference_genome=self.reference_genome)
        self.hgmd = TranscriptRelease.objects.create(release="2", source=self.hgmd_source,
                                                     reference_genome=self.reference_genome)

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
        
        expected_err = "Abandoning input because: hgnc release is a lower version than 2"
        with self.assertRaisesRegex(ValueError, expected_err):
            _check_for_transcript_seeding_version_regression(new_hgnc, new_gff, new_mane,
                                                        new_hgmd, self.reference_genome)
