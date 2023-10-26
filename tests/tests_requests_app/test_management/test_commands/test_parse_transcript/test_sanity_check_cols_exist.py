from django.test import TestCase

import pandas as pd

from requests_app.management.commands._parse_transcript import _sanity_check_cols_exist


class TestSanityCheckColsExist(TestCase):
    """
    Test out the formatter for column errors,
    used for several input files.
    We mostly use the MANE file set-up here.
    """

    hgnc_cols = ["HGNC ID", "Approved symbol", "Alias symbols"]
    hgnc_name = "HGNC dump"
    mane_cols = ["Gene", "MANE TYPE", "RefSeq StableID GRCh38 / GRCh37"]
    mane_name = "MANE"
    gene2refseq_cols = ["refcore", "refversion", "hgmdID"]
    gene2refseq_name = "gene2refseq"

    def test_passing_case(self):
        """
        Test that a dataframe which contains all the correct column names,
        correctly passes the sanity-checker.
        """
        test_mane = pd.DataFrame(
            {"Gene": [], "MANE TYPE": [], "RefSeq StableID GRCh38 / GRCh37": []}
        )
        assert not _sanity_check_cols_exist(test_mane, self.mane_cols, self.mane_name)

    def test_mane_missing_gene(self):
        """
        Test that a dataframe which misses the Gene column name,
        raises an AssertionError wtih the sanity-checker.
        """
        test_mane = pd.DataFrame(
            {"MANE TYPE": [], "RefSeq StableID GRCh38 / GRCh37": []}
        )
        with self.assertRaisesRegex(
            AssertionError, "Missing column Gene from MANE file - please check the file"
        ):
            _sanity_check_cols_exist(test_mane, self.mane_cols, self.mane_name)

    def test_mane_missing_mane_type(self):
        """
        Test that a dataframe which misses the MANE TYPE column name,
        raises an AssertionError with the sanity-checker.
        """
        test_mane = pd.DataFrame({"Gene": [], "RefSeq StableID GRCh38 / GRCh37": []})
        with self.assertRaisesRegex(
            AssertionError,
            "Missing column MANE TYPE from MANE file - please check the file",
        ):
            _sanity_check_cols_exist(test_mane, self.mane_cols, self.mane_name)

    def test_mane_missing_refseq(self):
        """
        Test that a dataframe which misses the RefSeq column name,
        raises an AssertionError with the sanity-checker.
        """
        test_mane = pd.DataFrame({"Gene": [], "MANE TYPE": []})
        with self.assertRaisesRegex(
            AssertionError,
            "Missing column RefSeq StableID GRCh38 / GRCh37 from MANE file - please check the file",
        ):
            _sanity_check_cols_exist(test_mane, self.mane_cols, self.mane_name)

    def test_mane_missing_several(self):
        """
        Test that a dataframe which misses several column names,
        raises an AssertionError with the sanity-checker.
        Every missing column should be printed in the output error message.
        """
        test_mane = pd.DataFrame({"Gene": []})
        with self.assertRaisesRegex(
            AssertionError,
            "Missing column MANE TYPE from MANE file - please check the file; "
            + "Missing column RefSeq StableID GRCh38 / GRCh37 from MANE file - "
            + "please check the file",
        ):
            _sanity_check_cols_exist(test_mane, self.mane_cols, self.mane_name)
