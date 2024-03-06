import json
from unittest import mock
from django.test import TestCase

from panels_backend.management.commands.panelapp import get_latest_version_panel

from .mockresponse import MockResponse


class TestGetLatestVersionPanel(TestCase):
    @mock.patch('requests.get')
    def test_get_latest_version_panel(self, mocked_panel):
        """
        Case: Fetch latest version given a panel id or specific version given a panel

        Expected behaviour: The function should return the latest version of a panel (mocked)
        """

        mocked_panel.return_value = MockResponse(
            json.load(open("testing_files/eris/panelapp_api_mocks/mock_panel.json")),
            200,
        )

        panel, is_superpanel = get_latest_version_panel(3)

        assert not is_superpanel
        assert panel.version == "4.0"
