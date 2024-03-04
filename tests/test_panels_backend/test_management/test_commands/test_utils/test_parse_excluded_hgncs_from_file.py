from django.test import TestCase
import pandas as pd
import unittest
import unittest.mock as mock

from panels_backend.management.commands.utils import (
    parse_excluded_hgncs_from_file,
)


class TestParseExcludedHgncsFromFile(TestCase):
    def setUp(self) -> None:
        # An example HGNC dataframe to use in the test
        self.hgnc_dataframe = pd.DataFrame(
            {
                "HGNC ID": pd.Series(
                    [
                        "HGNC:5",
                        "HGNC:37133",
                        "HGNC:24086",
                        "HGNC:6",
                        "HGNC:7",
                        "HGNC:27057",
                        "HGNC:7414",
                    ]
                ),
                "Approved name": pd.Series(
                    [
                        "alpha-1-B glycoprotein",
                        "A1BG antisense RNA 1",
                        "APOBEC1 complementation factor",
                        "symbol withdrawn, see [HGNC:12469](/data/gene-symbol-report/#!/"
                        + "hgnc_id/HGNC:12469)",
                        "alpha-2-macroglobulin",
                        "A2M antisense RNA 1",
                        "mitochondrially encoded ATP synthase membrane subunit 6",
                        # last entry should filter out
                    ]
                ),
                "RefSeq IDs": pd.Series(
                    [
                        "NM_130786",
                        "NR_015380",
                        "NM_014576",
                        "",
                        "NM_000014",
                        "NR_026971",
                        "YP_003024031",
                    ]
                ),
                "Locus type": pd.Series(
                    [
                        "gene with protein product",
                        "RNA, long non-coding",  # should filter out
                        "gene with protein product",
                        "unknown",
                        "gene with protein product",
                        "RNA, long non-coding",  # should filter out
                        "gene with protein product",
                    ]
                ),
            },
        )

    @mock.patch("panels_backend.management.commands.utils.pd.read_csv")
    def test_parse_hgncs(self, mock_read_csv):
        """
        CASE: A dataframe containing 7 entries is parsed. Two are RNAs, and
        one is mitochrondrially encoded.
        EXPECT: The HGNCs of the 3 entries described in CASE are returned as
        a set.
        """
        mock_read_csv.return_value = self.hgnc_dataframe
        expected = set(["HGNC:7414", "HGNC:37133", "HGNC:27057"])
        actual = parse_excluded_hgncs_from_file("/dev/null")
        self.assertListEqual(sorted(expected), sorted(actual))
