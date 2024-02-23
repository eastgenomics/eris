from django.test import TestCase
from unittest import mock
import pandas as pd

from panels_backend.management.commands.generate import (
    Command,
)


class TestCommandValidateHgnc(TestCase):
    """
    Tests for a function which checks whether a HGNC file
    is in a valid format or not.
    """

    def test_file_does_not_exist(self):
        """
        CASE: _validate_hgnc is called on a non-existent file
        EXPECT: the function returns False
        """
        hgnc = Command()
        with mock.patch("os.path.isfile") as mock_exists:
            mock_exists.return_value = False
            result = hgnc._validate_hgnc("/dev/null")
            assert not result

    def test_columns_are_missing(self):
        """
        CASE: the HGNC file exists, but necessary columns are missing
        EXPECT: a ValueError is raised with a message to warn the user
        that the HGNC file has some issues
        """
        hgnc = Command()
        with mock.patch("pandas.read_csv") as mock_read:
            # note that 'Approved name' is missing from cols in the mocked
            # DataFrame
            mock_read.return_value = pd.DataFrame(
                {"HGNC ID": pd.Series([]), "Locus type": pd.Series([])}
            )
            with mock.patch("os.path.isfile") as mock_exists:
                mock_exists.return_value = True
                with self.assertRaises(ValueError) as cm:
                    result = hgnc._validate_hgnc("/dev/null")
                self.assertEqual(
                    "Missing columns in HGNC file: ['Approved name']",
                    str(cm.exception),
                )

    def test_acceptable_hgnc_format(self):
        """
        CASE: HGNC file exists and has necessary columns
        EXPECT: the function returns True
        """
        hgnc = Command()
        with mock.patch("pandas.read_csv") as mock_read:
            mock_read.return_value = pd.DataFrame(
                {
                    "HGNC ID": pd.Series([]),
                    "Locus type": pd.Series([]),
                    "Approved name": pd.Series([]),
                }
            )
            with mock.patch("os.path.isfile") as mock_exists:
                mock_exists.return_value = True
                assert hgnc._validate_hgnc("/dev/null")
