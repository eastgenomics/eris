from django.test import TestCase
from unittest import mock
import json

from panels_backend.management.commands.panelapp import (
    _fetch_latest_signed_off_version_based_on_panel_id,
)
from .mockresponse import MockResponse


class TestFetchLatestSignedOffVersionBasedOnPanelId(TestCase):
    @mock.patch("requests.get")
    def test_general_function(self, mocked_response):
        """
        Case: Test that the function returns the latest signed-off version of a panel.
        Expected behaviour: The function should return version 1.7 (mocked response)
        """

        mocked_response.return_value = MockResponse(
            json.load(
                open(
                    "testing_files/eris/panelapp_api_mocks/mock_latest_signed_off_panel.json"
                )
            ),
            200,
        )

        panel_version = _fetch_latest_signed_off_version_based_on_panel_id(
            1141
        )

        assert panel_version == "1.7"

    @mock.patch("requests.get")
    def test_exception_raised(self, mocked_response):
        """
        Case: If API returned non-200 status code, raise Exception
        Expected behaviour: An Exception should be raised.
        """

        # mocked response should return an Exception rather than a response as that's what
        # returned by the function
        mocked_response.return_value = Exception(500)

        self.assertRaisesRegex(
            Exception,
            r"Could not fetch latest signed off panel based on panel 3*",
            _fetch_latest_signed_off_version_based_on_panel_id,
            3,
        )
