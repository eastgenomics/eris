import json
from unittest import mock
from django.test import TestCase

from panels_backend.management.commands.panelapp import (
    get_latest_version_panel,
    PanelClass,
)


class TestGetPanelFromUrl(TestCase):
    def get_latest_version_panel(self):
        """
        Case: Fetch latest version given a panel id or specific version given a panel

        NOTE: a bit of a weird test because these two functions
        - get_latest_version_panel
        - get_specific_version_panel
        are essentially the same function that call another function
        "get_panel_from_url" which is tested in test_get_panel_from_url.py

        In order for the test to work, it is necessary to mock the output for two functions
        nested within:
        - get_panel_from_url
        - _check_superpanel_status

        Expected behaviour: The function should return the latest version of a panel (mocked)
        """

        with mock.patch(
            "panels_backend.management.commands.panelapp.get_panel_from_url"
        ) as mocked_panel:
            with mock.patch(
                "panels_backend.management.commands.panelapp._check_superpanel_status"
            ) as mocked_superpanel_status:
                mocked_superpanel_status.return_value = (
                    False  # mocked panel is not a superpanel
                )

                mocked_panel.return_value = (
                    PanelClass(**{"id": 3, "version": "4.1"}),
                    False,
                )  # mocked returned panel

                panel, is_superpanel = get_latest_version_panel(3)

                assert not is_superpanel
                assert panel.version == "4.1"
