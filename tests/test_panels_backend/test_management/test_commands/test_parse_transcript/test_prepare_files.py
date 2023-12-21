from django.test import TestCase

from unittest import mock
import pandas as pd


from panels_backend.management.commands._parse_transcript import _prepare_mane_file


class TestBasicManeFile(TestCase):
    """
    Test that the MANE file prepares to the correct dict format
    """

    def test_basic_parsing_filtering(self):
        """
        Test that the correct output format is made.
        Also check that not-wanted MANE values (anything other than SELECT or PLUS CLINICAL)
        are discarded
        """
        with mock.patch("pandas.read_csv") as mock_df:
            mock_return = pd.DataFrame(
                {
                    "Gene": ["A1BG", "A1CF", "A2M"],
                    "MANE TYPE": [
                        "MANE SELECT",
                        "MANE PLUS CLINICAL",
                        "MANE SOME OTHER THING",
                    ],
                    "Ensembl StableID GRCh38": ["test", "test", "test"],
                    "RefSeq StableID GRCh38 / GRCh37": [
                        "NM_130786.4",
                        "NM_014576.4",
                        "NM_000014.6",
                    ],
                    "Ensembl StableID GRCh37 (Not MANE)": ["enst", "enst", "enst"],
                    "5'UTR": ["n", "n", "n"],
                    "CDS": ["y", "y", "y"],
                    "3'UTR": ["n", "n", "n"],
                }
            )
            mock_df.return_value = mock_return

            hgnc_ids = {"A1BG": "HGNC:1", "A1CF": "HGNC:2", "A2M": "HGNC:3"}

            mane_output = _prepare_mane_file("/dev/null", hgnc_ids)

            assert len(mane_output) == 2
            expected = [
                {
                    "HGNC ID": "HGNC:1",
                    "MANE TYPE": "MANE SELECT",
                    "RefSeq": "NM_130786.4",
                    "RefSeq_versionless": "NM_130786",
                },
                {
                    "HGNC ID": "HGNC:2",
                    "MANE TYPE": "MANE PLUS CLINICAL",
                    "RefSeq": "NM_014576.4",
                    "RefSeq_versionless": "NM_014576",
                },
            ]
            self.maxDiff = None
            # assertCountEqual lets the elements be in different orders -
            # normal assert will throw errors if the keys in a dict are
            # ordered differently
            self.assertCountEqual(mane_output, expected)
