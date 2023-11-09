from typing import Any
from django.test import TestCase

import numpy as np

from requests_app.models import (
    HgncRelease,
    GffRelease,
    TranscriptRelease,
    TranscriptSource,
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
        return super().setUp()
    
    def test_old_hgnc_release(self):
        """
        CASE: All user-provided releases are newer/same age as in db, EXCEPT the HGNC release
        is too old.
        EXPECT: Exception raised with an error for the HGNC release
        """