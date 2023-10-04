from django.test import TestCase
import numpy as np
import pandas as pd
from unittest.mock import patch

from requests_app.management.commands._parse_transcript import _prepare_mane_ftp_file


class TestManeFtpProduced(TestCase):
    """
    Test that FTP format files are correctly parsed to a dict
    """
    @patch('requests_app.management.commands._parse_transcript.pd.read_csv')
    def test_correct_parsing(self, mock_read_csv):
        """
        Check that our final dict emits correctly.
        Patch Pandas read_csv to mock out the dataframe within the function call.
        """
        mock_read_csv.return_value = pd.DataFrame({"MANE_Select_RefSeq_acc": 
                                                    pd.Series(["NM0001.1", "NM0002.1"])})
        output = _prepare_mane_ftp_file("/dev/null", "1.0")
        assert type(output) == list
        assert output == [
            {"tx": "NM0001.1", "tx_base": "NM0001", "tx_version": "1", "mane_release": "1.0"}, 
            {"tx": "NM0002.1", "tx_base": "NM0002", "tx_version": "1", "mane_release": "1.0"}
            ]
