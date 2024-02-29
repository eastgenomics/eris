from django.test import TestCase
from unittest import mock
import json

from panels_backend.management.commands.panelapp import _get_all_signed_off_panels
from .mockresponse import MockResponse


class TestGetAllSignedOffPanel(TestCase):

    @mock.patch('requests.get')
    def test_general_function(self, mocked_response):
        """
        Case: Test that the function returns a list of panels.
        Expected behaviour: The function should return a list of 100 panels.
        """

        mocked_response.return_value = MockResponse(
            json.load(
                open('testing_files/eris/panelapp_api_mocks/mock_panelapp_api.json')
            ),
            200,
        )

        panels = _get_all_signed_off_panels()

        assert len(panels) == 100  # there are 100 panels in the mock file

    @mock.patch('requests.get')
    def test_exception_raised(self, mocked_response):
        """
        Case: If API returned non-200 status code, raise Exception
        Expected behaviour: An Exception should be raised.
        """

        mocked_response.return_value = MockResponse(
            json.load(
                open('testing_files/eris/panelapp_api_mocks/mock_panelapp_api.json')
            ),
            201,
        )

        self.assertRaises(Exception, _get_all_signed_off_panels)
