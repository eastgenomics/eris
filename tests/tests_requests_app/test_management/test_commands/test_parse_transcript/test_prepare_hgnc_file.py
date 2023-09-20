from django.test import TestCase

import pandas as pd

from requests_app.management.commands._parse_transcript import \
    _sanity_check_hgnc_file


class TestSanityCheckHgncFile(TestCase):
    """
    Tests for function _sanity_check_hgnc_file
    """
    def test_passing_case(self):
        test_pd = pd.DataFrame({"HGNC ID": [], "Approved symbol": [], "Alias symbols": []})
        assert not _sanity_check_hgnc_file(test_pd)
        
    def test_missing_hgnc_id(self):
        test_pd = pd.DataFrame({"HGNC or something": [], "Approved symbol": [], "Alias symbols": []})
        with self.assertRaisesRegex(AssertionError, "Missing HGNC ID column. Check HGNC dump file"): 
            _sanity_check_hgnc_file(test_pd)

    def test_missing_approved_symbols(self):
        test_pd = pd.DataFrame({"HGNC ID": [], "Approve these symbols": [], "Alias symbols": []})
        with self.assertRaisesRegex(AssertionError, "Missing Approved symbol column. Check HGNC dump file"): 
            _sanity_check_hgnc_file(test_pd)

    def test_missing_alias_symbols(self):
        test_pd = pd.DataFrame({"HGNC ID": [], "Approved symbol": [], "Alias things": []})
        with self.assertRaisesRegex(AssertionError, "Missing Alias symbols column. Check HGNC dump file"): 
            _sanity_check_hgnc_file(test_pd)
    
    def test_missing_multiple(self):
        # Checks that we get multiple errors, where several things are wrong
        test_pd = pd.DataFrame({"HGNC ID": [], "A missing field": [], "Alias things": []})
        with self.assertRaisesRegex(AssertionError, 
                                        "Missing Approved symbol column. Check HGNC dump file; " +
                                        "Missing Alias symbols column. Check HGNC dump file"
                                    ): 
            _sanity_check_hgnc_file(test_pd)
    
    
