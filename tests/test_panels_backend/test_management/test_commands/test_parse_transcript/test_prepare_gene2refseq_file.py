from django.test import TestCase
from unittest import mock
import pandas as pd

from panels_backend.management.commands._parse_transcript import (
    _prepare_gene2refseq_file,
)


class TestPrepareGene2RefSeqFile(TestCase):
    """
    Test that _prepare_gene2refseq_file returns the expected types
    """

    def setUp(self) -> None:
        self.sample_file_path = "testing_files/eris/sample_gene2refseq.csv"

    def test_expected_output_straightforward(self):
        """
        CASE: A very short version of the file is parsed.
        EXPECT: A dictionary of hgmd id to a list-of-lists.
        The base-list contains 2 items, refcore and refversion.
        The format of the output is dict[str, list[str]].
        """
        expected = {"1": [["NM_145891", "2"]], "2": [["NM_000014", "5"]]}
        result = _prepare_gene2refseq_file(self.sample_file_path)
        self.assertEqual(expected, result)

    def test_expected_column_error(self):
        """
        CASE: The file is missing 2 required columns (refcore and
        refversion)
        EXPECT: A handy error is output to tell which cols are missing
        """
        with mock.patch("pandas.read_csv") as mock_df:
            mock_return = pd.DataFrame(
                {
                    "hgmdID": ["1"],
                }
            )
            mock_df.return_value = mock_return

            expected_err = (
                f"Missing columns in gene2refseq: \['refcore', 'refversion'\]"
            )
            with self.assertRaisesRegex(ValueError, expected_err):
                result = _prepare_gene2refseq_file("/dev/null")
