from django.test import TestCase
import requests
from unittest import mock
from unittest.mock import Mock, MagicMock
import numpy as np
import json


from requests_app.management.commands.panelapp import get_panel


class TestGetPanel_ErrorsOnSpecificSuperpanel(TestCase):
    """
    We don't allow the user to specify a version of a single superpanel,
    because of PanelApp API limitations.
    Test that an error is raised if the user attempts this.
    """
    def test_errors_on_superpanel_version(self):
        """
        CASE: User tries to request a non signed off superpanel, via specific-version request
        EXPECT: Function aborts with error message
        """
        expected_err = "Aborting because specific versions of superpanels cannot be requested - "
        "to get the most-recently signed-off superpanel, please run the command again without"
        "a version"
        with self.assertRaisesRegex(ValueError, expected_err):
            with mock.patch("requests_app.management.commands.panelapp._check_superpanel_status") as mock_status:
                mock_status.return_value  = True
                with mock.patch("requests.get") as mock_request_get:
                    mock_request_get.return_value.json_data = \
                        json.load(open("testing_files/panelapp_api_mocks/superpanel_842_v13.4.json"))
                    mock_request_get.return_value.status_code = 200
                    get_panel(842, 13.4)


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
            with mock.patch("requests_app.management.commands.panelapp._check_superpanel_status") as mock_status:
                mock_status.return_value  = True
                with mock.patch("requests.get") as mock_request_get:
                    mock_request_get.return_value.json_data = \
                        json.load(open("testing_files/panelapp_api_mocks/superpanel_842_v13.4.json"))
                    mock_request_get.return_value.status_code = 500
                    get_panel(842, 13.4)