from django.test import TestCase

import pandas as pd

from requests_app.management.commands._parse_transcript import check_missing_columns


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
        assert not check_missing_columns(test_mane, self.mane_cols)

    def test_mane_missing_gene(self):
        """
        Case: Example df is missing a "Gene" column
        Expect: Function to return a list containing the missing column "Gene" only
        """
        test_mane = pd.DataFrame(
            {"MANE TYPE": [], "RefSeq StableID GRCh38 / GRCh37": []}
        )

        assert check_missing_columns(test_mane, self.mane_cols) == ["Gene"]

    def test_mane_missing_mane_type(self):
        """
        Case: Example df is missing a "MANE TYPE" column
        Expect: Function to return a list containing the missing column "MANE TYPE" only
        """
        test_mane = pd.DataFrame({"Gene": [], "RefSeq StableID GRCh38 / GRCh37": []})

        assert check_missing_columns(test_mane, self.mane_cols) == ["MANE TYPE"]

    def test_mane_missing_refseq(self):
        """
        Case: Example df is missing a "RefSeq StableID GRCh38 / GRCh37" column
        Expect: Function to return a list containing the missing column "RefSeq StableID GRCh38 / GRCh37" only
        """
        test_mane = pd.DataFrame({"Gene": [], "MANE TYPE": []})

        assert check_missing_columns(test_mane, self.mane_cols, self.mane_name) == [
            "RefSeq StableID GRCh38 / GRCh37"
        ]

    def test_mane_missing_several_columns(self):
        """
        Case: Example df is missing several columns:
            - RefSeq StableID GRCh38 / GRCh37
            - MANE TYPE
        Expect: Function to return a list containing the missing column "RefSeq StableID GRCh38 / GRCh37" only
        """
        test_mane = pd.DataFrame({"Gene": []})

        check_missing_columns(test_mane, self.mane_cols) == [
            "MANE TYPE",
            "RefSeq StableID GRCh38 / GRCh37",
        ]
