from django.test import TestCase

import pandas as pd

from requests_app.management.commands._parse_transcript import \
    _sanity_check_mane_file


class TestSanityCheckManeFile(TestCase):
    """
    Run checks on the sanity-checking for MANE files.
    """
    def test_passing_case(self):
        test_mane = pd.DataFrame({"Gene": [], "MANE TYPE": [], "RefSeq StableID GRCh38 / GRCh37": []})
        assert not _sanity_check_mane_file(test_mane)
