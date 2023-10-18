from django.test import TestCase
import requests
from unittest.mock import MagicMock
import numpy as np
import json


from requests_app.management.commands.panelapp import \
    SuperPanelClass


def returns_example_superpanel():
    """
    Calls a known API endpoint for a superpanel
    and returns response.json()
    """
    api_url="https://panelapp.genomicsengland.co.uk/api/v1/panels/"
    panel_num="465"
    version="19.155"
    panel_url = f"{api_url}{panel_num}/?version={version}&format=json"
    response = requests.get(panel_url)
    return response.json()


def mocked_requests_get_superpanel(filename):
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
            "testing_files/panelapp_api_mocks/superpanel_api_example_most_genes_removed.json"
        )
        superpanel = SuperPanelClass(**json_response)

        assert superpanel.id == 465
        assert superpanel.name == "Other rare neuromuscular disorders"
        assert superpanel.version == "19.155"
        assert superpanel.panel_source == None

    def test_multiple_genes_one_panel(self):
        """
        Check that the SuperPanelClass correctly populates its list of child Panels,
        when we're dealing with several genes from the same sub-panel.
        EXPECT: 1 child Panel with multiple genes.
        """
        json_response = mocked_requests_get_superpanel(
            "testing_files/panelapp_api_mocks/superpanel_api_example_most_genes_removed.json"
        )
        superpanel = SuperPanelClass(**json_response)

        component_panels = superpanel.create_component_panels(superpanel.genes,
                                                              superpanel.regions)
        
        # our test data contains only 2 genes, and these are both for the same panel
        # there are no regions in the test data
        assert len(component_panels) == 1
        assert len(component_panels[0].genes) == 2

        # constituent panels are a list of PanelClass objects
        # and the data they store in 'genes' and 'regions' is a list-of-dicts
        first_panel = component_panels[0]
        assert first_panel.id == 66
        assert first_panel.name == "Rhabdomyolysis and metabolic muscle disorders"
        assert first_panel.version == "3.37"
        assert first_panel.panel_source == "PanelApp"

        first_panels_genes = component_panels[0].genes
        assert first_panels_genes[0]["gene_data"]["hgnc_id"] == "HGNC:21497"
        assert first_panels_genes[0]["gene_data"]["gene_name"] == "acyl-CoA dehydrogenase family member 9"

    def test_multiple_regions_one_panel(self):
        """
        Check that the class correctly populates its list of child Panels,
        when we're dealing with several regions from the same sub-panel.
        EXPECT: 1 child Panel with multiple regions.
        """
        json_response = mocked_requests_get_superpanel(
            "testing_files/panelapp_api_mocks/superpanel_api_example_most_regions_removed.json"
        )
        superpanel = SuperPanelClass(**json_response)

        component_panels = superpanel.create_component_panels(superpanel.genes,
                                                              superpanel.regions)
        
        # our test data contains only 2 regions, and these are both for the same panel
        # the genes are removed from the test data so shouldn't affect anything
        assert len(component_panels) == 1

        assert len(component_panels[0].regions) == 2

        # constituent panels are a list of PanelClass objects
        # and the data they store in 'genes' and 'regions' is a list-of-dicts
        first_panel = component_panels[0]
        assert first_panel.id == 79
        assert first_panel.name == "Paediatric motor neuronopathies"
        assert first_panel.version == "3.4"
        assert first_panel.panel_source == "PanelApp"

        first_panels_regions = component_panels[0].regions
        assert first_panels_regions[0]["entity_name"] == "ISCA-37404-Loss"
        assert first_panels_regions[0]["verbose_name"] == \
            "15q11q13 recurrent (PWS/AS) region (BP1-BP3, Class 1) Loss"
        assert first_panels_regions[0]["type_of_variants"] =="cnv_loss"

    def test_gene_and_region_from_same_panel(self):
        """
        A situation where some panels and genes are from the same panel.
        EXPECT: 1 gene and 1 region from the same panel should append correctly 
        to the same, single PanelClass object.
        """
        json_response = mocked_requests_get_superpanel(
            "testing_files/panelapp_api_mocks/superpanel_api_example_gene_region_same_panel.json"
        )
        superpanel = SuperPanelClass(**json_response)
        component_panels = superpanel.create_component_panels(superpanel.genes,
                                                              superpanel.regions)
        
        # our test data contains only 2 regions, and these are both for the same panel
        # the genes are removed from the test data so shouldn't affect anything
        assert len(component_panels) == 1

        assert len(component_panels[0].genes) == 1
        assert len(component_panels[0].regions) == 1

        first_panel = component_panels[0]
        assert first_panel.id == 79
        assert first_panel.name == "Paediatric motor neuronopathies"
        assert first_panel.version == "3.4"
        assert first_panel.panel_source == "PanelApp"

        first_panel_genes = first_panel.genes
        assert len(first_panel_genes) == 1
        assert first_panel_genes[0]["gene_data"]["hgnc_id"] == "HGNC:735"
        assert first_panel_genes[0]["gene_data"]["gene_name"] == \
            "N-acylsphingosine amidohydrolase 1"

        first_panels_regions = component_panels[0].regions
        assert first_panels_regions[0]["entity_name"] == "ISCA-37404-Loss"
        assert first_panels_regions[0]["verbose_name"] == \
            "15q11q13 recurrent (PWS/AS) region (BP1-BP3, Class 1) Loss"
        assert first_panels_regions[0]["type_of_variants"] == "cnv_loss"

    def test_gene_occurs_in_more_than_one_panel(self):
        """
        A situation where a gene appears in TWO subpanels
        EXPECT: gene to be attributed to both panels, with info such as MOI 
        separated out correctly
        """
        json_response = mocked_requests_get_superpanel(
            "testing_files/panelapp_api_mocks/superpanel_api_example_one_gene_two_panels.json"
        )
        superpanel = SuperPanelClass(**json_response)
        component_panels = superpanel.create_component_panels(superpanel.genes,
                                                              superpanel.regions)
        
        assert len(component_panels) == 2

        first_panel = component_panels[0]
        assert first_panel.id == 225
        assert first_panel.name == "Congenital myopathy"
        assert first_panel.version == "4.31"
        assert first_panel.panel_source == "PanelApp"

        first_panel_genes = first_panel.genes
        assert len(first_panel_genes) == 1
        assert first_panel_genes[0]["gene_data"]["hgnc_id"] == "HGNC:3756"
        assert first_panel_genes[0]["gene_data"]["gene_name"] == \
            "filamin C"

        second_panel = component_panels[1]
        assert second_panel.id == 185
        assert second_panel.name == \
            "Limb girdle muscular dystrophies, myofibrillar myopathies and distal myopathies"
        assert second_panel.version == "4.22"
        assert second_panel.panel_source == "PanelApp"

        second_panel_genes = second_panel.genes
        assert len(second_panel_genes) == 1
        assert second_panel_genes[0]["gene_data"]["hgnc_id"] == "HGNC:3756"
        assert second_panel_genes[0]["gene_data"]["gene_name"] == \
            "filamin C"


    def test_region_occurs_in_more_than_one_panel(self):
        """
        A situation where a region appears in TWO subpanels
        EXPECT: region to be attributed to both panels, with info such as MOI 
        separated out correctly
        NOTE that the example regions file here was made by duplicating a region
         from 'superpanel_api_example_one_gene_two_panels.json; and then
        changing the panel in the JSON, while the other files were just made 
        by deleting sections of 'real' API calls
        """
        json_response = mocked_requests_get_superpanel(
            "testing_files/panelapp_api_mocks/superpanel_api_example_one_region_two_panels.json"
        )
        superpanel = SuperPanelClass(**json_response)
        component_panels = superpanel.create_component_panels(superpanel.genes,
                                                              superpanel.regions)
        
        assert len(component_panels) == 2

        first_panel = component_panels[0]
        assert first_panel.id == 79
        assert first_panel.name == "Paediatric motor neuronopathies"
        assert first_panel.version == "3.4"
        assert first_panel.panel_source == "PanelApp"

        first_panel_regions = first_panel.regions
        assert len(first_panel_regions) == 1
        assert first_panel_regions[0]["entity_name"] == "ISCA-37404-Loss"

        second_panel = component_panels[1]
        assert second_panel.id == 100
        assert second_panel.name == \
            "Other motor neuronopathies"
        assert second_panel.version == "3.6"
        assert second_panel.panel_source == "PanelApp"

        second_panel_regions = second_panel.regions
        assert len(second_panel_regions) == 1
        assert second_panel_regions[0]["entity_name"] == "ISCA-37404-Loss"
    