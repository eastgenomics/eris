import json

from django.test import TestCase
from unittest import mock

from panels_backend.management.commands.panelapp import (
    get_panel_from_url,
    PanelClass,
)
from .mockresponse import MockResponse


class TestGetPanelFromUrl(TestCase):
    @mock.patch('requests.get')
    def test_fetching_panel(self, mocked_response):
        """
        Case: Fetch a panel from PanelApp
        Expected behaviour: The function should return a PanelClass object with id 3
        Mocked panel is not a superpanel
        """

        mocked_response.return_value = MockResponse(
            json.load(open('testing_files/eris/panelapp_api_mocks/mock_panel.json')),
            200,
        )
        panel, is_superpanel = get_panel_from_url(
            "https://panelapp.genomicsengland.co.uk/api/v1/panels/3/?format=json"
        )

        assert panel.id == 3
        assert not is_superpanel

    @mock.patch('requests.get')
    def test_fetching_superpanel(self, mocked_response):
        """
        Case: Fetch a superpanel from PanelApp
        Expected behaviour: The function should return a SuperPanelClass object with id 465
        Mocked panel is a superpanel

        # NOTE: mocked_version does not require a return value because it will not affect the test
        """
        with mock.patch(
            'panels_backend.management.commands.panelapp._fetch_latest_signed_off_version_based_on_panel_id'
        ) as _:
            with mock.patch(
                'panels_backend.management.commands.panelapp.get_specific_version_panel'
            ) as mocked_panel:

                mocked_panel.return_value = (
                    PanelClass(),
                    None,
                )  # to not affect the test

                mocked_response.return_value = MockResponse(
                    json.load(
                        open(
                            'testing_files/eris/panelapp_api_mocks/superpanel_api_mock.json'
                        )
                    ),
                    200,
                )
                superpanel, is_superpanel = get_panel_from_url(
                    "https://panelapp.genomicsengland.co.uk/api/v1/panels/465/?format=json"
                )

                assert superpanel.id == 465
                assert is_superpanel
