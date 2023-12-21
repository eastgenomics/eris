from django.test import TestCase
import requests
import json


from requests_app.management.commands.panelapp import SuperPanelClass


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
    return mock.json()


class TestSuperPanelClass(TestCase):
    """
    Tests for superpanel parsing.
    Trying out scenarios with multiple genes per panel, multiple regions per panel,
    and a more complex scenario, with multiple panels and regions for multiple panels.
    """

    def test_basic_values_parse(self):
        """
        Check that basic SuperPanel string values, such as ID, are parsed correctly
        """
        # mocked-out API call
        json_response = mocked_requests_get_superpanel(
            "testing_files/eris/panelapp_api_mocks/superpanel_api_example_most_genes_removed.json"
        )
        superpanel = SuperPanelClass(**json_response)

        assert superpanel.id == 465
        assert superpanel.name == "Other rare neuromuscular disorders"
        assert superpanel.version == "19.155"
        assert superpanel.panel_source is None

    def test_children_panel_ids_retrieved_in_superpanel_is_correct(self):
        """
        Superpanel should have a list of child panels (list[PanelClass])
        Each child panel should have an ID
        Check that the IDs are correct
        """

        # mocked-out API call
        json_response = mocked_requests_get_superpanel(
            "testing_files/eris/panelapp_api_mocks/superpanel_api_mock.json"
        )
        superpanel = SuperPanelClass(**json_response)

        assert set([p.id for p in superpanel.child_panels]) == set(
            [66, 79, 185, 207, 225, 232, 235]
        )
