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

    def test_missing_gene(self):
        test_mane = pd.DataFrame({"MANE TYPE": [], "RefSeq StableID GRCh38 / GRCh37": []})
        with self.assertRaisesRegex(AssertionError, "Missing Gene column. Check MANE file"): 
            _sanity_check_mane_file(test_mane)

    def test_missing_mane_type(self):
        test_mane = pd.DataFrame({"Gene": [], "RefSeq StableID GRCh38 / GRCh37": []})
        with self.assertRaisesRegex(AssertionError, "Missing MANE TYPE column. Check MANE file"): 
                    _sanity_check_mane_file(test_mane)
    
    def test_missing_refseq(self):
        test_mane = pd.DataFrame({"Gene": [], "MANE TYPE": []})
        with self.assertRaisesRegex(AssertionError, "Missing RefSeq column. Check MANE file"): 
            _sanity_check_mane_file(test_mane)

    def test_missing_several(self):
        test_mane = pd.DataFrame({"Gene": []})
        with self.assertRaisesRegex(AssertionError, "Missing MANE TYPE column. Check MANE file; " + 
                                    "Missing RefSeq column. Check MANE file"): 
            _sanity_check_mane_file(test_mane)

