import json
from django.test import TestCase

from panels_backend.management.commands.panelapp import _check_superpanel_status


class TestCheckSuperpanelStatus(TestCase):
    def test_with_an_actual_superpanel(self):
        """
        Case: Test that the function returns True if the panel is a superpanel.
        Expected behaviour: The function should return True.
        """

        response = json.load(
            open(
                'testing_files/eris/panelapp_api_mocks/superpanel_api_mock.json'
            )  # mocked superpanel
        )

        is_superpanel = _check_superpanel_status(response)

        assert is_superpanel

    def test_with_a_normal_panel(self):
        """
        Case: Test that the function returns False if the panel is not superpanel.
        Expected behaviour: The function should return True.
        """

        response = json.load(
            open(
                'testing_files/eris/panelapp_api_mocks/mock_panel.json'
            )  # mocked panel
        )

        is_superpanel = _check_superpanel_status(response)

        assert not is_superpanel
