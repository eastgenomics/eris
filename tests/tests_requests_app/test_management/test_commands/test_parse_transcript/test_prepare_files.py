from django.test import TestCase

from unittest.mock import patch
import pandas as pd


from requests_app.management.commands._parse_transcript import _prepare_mane_file


class TestBasicManeFile_RunsWithSomeFilter(TestCase):
    """
    For a very basic dataframe, check we get the correct type of 
    output dictionary.
    """
    def test_basic_mane_output(self):
        """
        Check basic parsing is carried out
        Note the filtering of odd MANE types is tested, as is 
        the discarding of unused cols
        """
        mane_file = "/dev/null"
        hgnc_symbol_to_hgnc_id = {"A1BG": "HGNC:5",
                                "A1BG-AS1": "HGNC:37133",
                                "A1CF": "HGNC:24086"}
        with patch("pandas.read_csv") as mock_read_csv:
            mock_read_csv.return_value = pd.DataFrame(
                {
                    "Gene": pd.Series(["A1BG", "A1BG-AS1", "A1CF"]),
                    "MANE TYPE": pd.Series(["MANE SELECT", "MANE PLUS CLINICAL", "MANE Unnecessary"]),
                    "RefSeq StableID GRCh38 / GRCh37": pd.Series(["NM0001.1", "NM0030.1", "NM0050.1"])
                }
            )
            result = _prepare_mane_file(mane_file, hgnc_symbol_to_hgnc_id)

            expected = pd.DataFrame(
                {
                  "Gene": pd.Series(["A1BG", "A1BG-AS1"]),
                  "MANE TYPE": pd.Series(["MANE SELECT", "MANE PLUS CLINICAL"]),
                  "RefSeq StableID GRCh38 / GRCh37": pd.Series(["NM0001.1", "NM0030.1"]),
                  "HGNC_ID": pd.Series(["HGNC:5", "HGNC:37133"])
                }
            )

            pd.testing.assert_frame_equal(result, expected)

