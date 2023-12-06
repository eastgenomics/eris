from django.test import TestCase
from unittest import mock
from unittest.mock import Mock, MagicMock
import numpy as np
import json

from requests_app.management.commands.panelapp import get_specific_version_panel


class TestGetPanel_ErrorsNot200(TestCase):
    """
    Print error if a non-OK API code is returned
    """

    def test_errors_on_superpanel_version(self):
        """
        CASE: A non-200 code returns from API
        EXPECT: Function exits 1. Note I haven't tested the error text exactly.
        """
        expected_exit_code = "1"
        with self.assertRaisesRegex(SystemExit, expected_exit_code):
            with mock.patch(
                "requests_app.management.commands.panelapp._check_superpanel_status"
            ) as mock_status:
                # patch over the internally-called function '_check_superpanel_status'
                mock_status.return_value = True
                with mock.patch("requests.get") as mock_request_get:
                    # patch over the internally-called 'requests.get'
                    mock_request_get.return_value.json_data = json.load(
                        open(
                            "testing_files/panelapp_api_mocks/superpanel_842_v13.4.json"
                        )
                    )
                    mock_request_get.return_value.status_code = 500
                    get_specific_version_panel(842, 13.4)
