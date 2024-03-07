from django.test import TestCase
import pandas as pd
from unittest import mock

from panels_backend.management.commands._parse_transcript import (
    _prepare_markname_file,
)


class TestPrepareMarknameFile(TestCase):
    """
    Test that _prepare_markname_file returns the expected types
    """

    def setUp(self) -> None:
        self.sample_file_path = "testing_files/eris/sample_markname.csv"

    def test_expected_output_straightforward(self):
        """
        CASE: A very short version of the file is parsed.
        EXPECT: A dictionary containing string-keys with values that are lists of strings.
        """
        expected = {18222: [1], 7: [2]}
        result = _prepare_markname_file(self.sample_file_path)
        self.assertEqual(expected, result)

    def test_expected_column_error(self):
        """
        CASE: The file is missing a required column, hgnc ID
        EXPECT: A handy error is output to tell which cols are missing
        """
        with mock.patch("pandas.read_csv") as mock_df:
            mock_return = pd.DataFrame(
                {
                    "gene_id": [1, 2],
                }
            )
            mock_df.return_value = mock_return

            expected_err = f"Missing columns in markname: \['hgncID'\]"
            with self.assertRaisesRegex(ValueError, expected_err):
                result = _prepare_markname_file("/dev/null")
