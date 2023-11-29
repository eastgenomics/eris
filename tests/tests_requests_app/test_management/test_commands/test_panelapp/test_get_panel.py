from django.test import TestCase
import requests
from unittest import mock
from unittest.mock import Mock, MagicMock
import numpy as np
import json


from requests_app.management.commands.panelapp import get_panel

def mocked_requests_get_superpanel(filename):
    """
    Makes a pretend API response which contains some file contents
    as its json payload.
    Lets you avoid actually calling the real PanelApp API.
    """
    class MockResponse:
        def __init__(self):
            self.json_data = json.load(open(filename))
            self.status_code = 200

        def json(self):
            return self.json_data

    mock = MockResponse()
    return mock


class TestGetPanel_ErrorsOnSpecificSuperpanel(TestCase):
    """
    We don't allow the user to specify a version of a superpanel,
    because of PanelApp API limitations.
    Test that an error is raised if this happens.
    """  
    def test_errors_on_superpanel_version(self):
        #TODO: find a way to mock out
        expected_err = "Aborting because specific versions of superpanels cannot be requested - "
        "to get the most-recently signed-off superpanel, please run the command again without"
        "a version"
        with self.assertRaisesRegex(ValueError, expected_err):
            get_panel(842, 13.4)