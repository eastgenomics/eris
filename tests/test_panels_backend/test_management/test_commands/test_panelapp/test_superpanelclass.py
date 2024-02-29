from django.test import TestCase
import json
from unittest import mock


from panels_backend.management.commands.panelapp import (
    SuperPanelClass,
    PanelClass,
)
from .mockresponse import MockResponse


class TestSuperPanelClass(TestCase):
    """
    Tests for superpanel parsing.
    Trying out scenarios with multiple genes per panel, multiple regions per panel,
    and a more complex scenario, with multiple panels and regions for multiple panels.
    """

    def test_basic_values_parse(self):
        """
        Check that basic SuperPanel string values, such as ID, are parsed correctly
        SuperPanelClass will call _create_component_panels() to fetch the child panels
        _create_component_panels() will call two more functions:
        - _fetch_latest_signed_off_version_based_on_panel_id
        - get_specific_version_panel

        These two functions need to be mocked out in order to not fail the test when
        API calling failed.


        """
        with mock.patch(
            "panels_backend.management.commands.panelapp._fetch_latest_signed_off_version_based_on_panel_id"
        ) as _:
            with mock.patch(
                "panels_backend.management.commands.panelapp.get_specific_version_panel"
            ) as mocked_panel:
                mocked_panel.return_value = (PanelClass(), None)

                # mocked-out API call
                superpanel = SuperPanelClass(
                    **MockResponse(
                        json.load(
                            open(
                                "testing_files/eris/panelapp_api_mocks/superpanel_api_example_most_genes_removed.json"
                            )
                        ),
                    ).json()
                )

                assert superpanel.id == 465
                assert superpanel.name == "Other rare neuromuscular disorders"
                assert superpanel.version == "19.155"
                assert superpanel.panel_source is None

    def test_children_panel_ids_retrieved_in_superpanel_is_correct(self):
        """
        Superpanel should have a list of child panels (list[PanelClass])
        The function does not take the child panels directly from the API response
        returned for SuperPanel because SuperPanel does not returned the latest
        signed-off version of the panels. Instead, it needs to call the API again
        to check the latest signed-off version of each child panel.

        Therefore the child panels are not parsed in the __init__ method, but in
        the _create_component_panels method.

        This stage need to be mocked out in order to not fail the test when
        API calling failed.
        """
        with mock.patch(
            "panels_backend.management.commands.panelapp._fetch_latest_signed_off_version_based_on_panel_id"
        ) as _:
            with mock.patch(
                "panels_backend.management.commands.panelapp.get_specific_version_panel"
            ) as mocked_panel:
                mocked_panel.return_value = (
                    PanelClass(**{"id": 3}),
                    None,
                )  # mocked child panel insertion

                # mocked-out API call
                superpanel = SuperPanelClass(
                    **MockResponse(
                        json.load(
                            open(
                                "testing_files/eris/panelapp_api_mocks/superpanel_api_example_most_genes_removed.json"
                            )
                        ),
                    ).json()
                )

                assert superpanel.child_panels[0].id == 3
