from django.test import TestCase
from django.contrib.auth.models import User
from unittest import mock
import pandas as pd

from panels_backend.models import Gene, HgncRelease
from panels_backend.management.commands._parse_transcript import (
    _prepare_gff_file,
)


class TestPrepareGffFile(TestCase):
    """
    Test the function prepare_hgnc_file in _parse_transcript.py
    """

    def setUp(self) -> None:
        return None

    def test_prepare_invalid_format(self):
        """
        CASE: Pass a GFF which is missing an important column
        EXPECT: Raises a ValueError complaining about the column
        """
        with mock.patch("pandas.read_csv") as mock_df:
            mock_return = pd.DataFrame(
                {
                    "chrome": ["1"],
                    "start": ["65559"],
                    "end": ["65578"],
                    "transcript": ["NM_001005484.2"],
                    "exon": ["2"],
                }
            )
            mock_df.return_value = mock_return
            expected_err = "Missing columns in GFF: \['hgnc'\]"
            with self.assertRaisesRegex(ValueError, expected_err):
                _prepare_gff_file("/dev/null")

    def test_reads_standard_gff(self):
        """
        CASE: Pass a complete GFF
        EXPECT: Returns the reformatted data
        """
        with mock.patch("pandas.read_csv") as mock_df:
            mock_return = pd.DataFrame(
                {
                    "chrome": ["1", "1"],
                    "start": ["65559", "65559"],
                    "end": ["65578", "65578"],
                    "hgnc": ["HGNC:14825", "HGNC:14825"],
                    "transcript": ["NM_001005484.2", "NM_0000.0"],
                    "exon": ["2", "2"],
                }
            )
            mock_df.return_value = mock_return

            gff = _prepare_gff_file("/dev/null")
            expected_gff = {"HGNC:14825": ["NM_001005484.2", "NM_0000.0"]}

            self.assertCountEqual(gff, expected_gff)
