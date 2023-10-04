"""
This file test the function `_make_panels_from_hgncs` in the file `requests_app/management/commands/_insert_ci.py`

Tested scenario:
- core function of making panels from a list of hgncs and linking it to a clinical indication
- scenario where a new list of hgncs is given to an existing clinical indication (that is already in the db)
"""

from django.test import TestCase

from requests_app.management.commands.utils import sortable_version
from requests_app.models import (
    ClinicalIndication,
    Panel,
    ClinicalIndicationPanel,
    Gene,
    PanelGene,
    PanelGeneHistory,
    ClinicalIndicationPanelHistory,
)
from requests_app.management.commands._insert_ci import _make_panels_from_hgncs
from tests.tests_requests_app.test_management.test_commands.test_insert_panel.test_insert_gene import (
    len_check_wrapper,
    value_check_wrapper,
)


class TestMakePanelsFromHgncs(TestCase):
    """
    The core function is to make panels from a list of hgncs.
    example: if a clinical indication has hgnc:1 and hgnc2 in its panel list
    this function will create a panel named "hgnc:1,hgnc:2" and link it to the clinical indication

    we should expect to see a clinical indication-panel relationship in the database

    if the same clinical indication gets the same panel (same list of hgncs), nothing should be changed
    if the same clinical indication gets a different panel (different), new link should be generated but flagged for review (new and old links)

    """

    def setUp(self) -> None:
        self.first_clinical_indication = ClinicalIndication.objects.create(
            r_code="R123",
            name="Test CI",
            test_method="Test method",
        )

    def test_make_panel_function(self):
        """
        Given a list of hgncs, make a panel and link it to the clinical indication
        """
        errors = []

        mock_test_directory = {
            "td_source": "rare-and-inherited-disease-national-gnomic-test-directory-v5.1.xlsx",
            "config_source": "230401_RD",
            "date": "230616",
        }

        _make_panels_from_hgncs(
            mock_test_directory,
            self.first_clinical_indication,
            ["HGNC:1", "HGNC:2"],
        )

        panels = Panel.objects.all()

        errors += len_check_wrapper(panels, "panel", 1)
        errors += value_check_wrapper(
            panels[0].panel_name,
            "panel name",
            "HGNC:1,HGNC:2",
        )  # panel name should be the list of hgncs joined by comma

        errors += value_check_wrapper(
            panels[0].test_directory,
            "panel test directory",
            True,
        )  # panel's test directory col should be True because this panel is made from test directory seed

        errors += len_check_wrapper(
            PanelGeneHistory.objects.all(), "panel-gene history records", 2
        )  # should have two history recorded HGNC:1 and HGNC:2

        links = ClinicalIndicationPanel.objects.all()

        errors += len_check_wrapper(
            links, "clinical indication-panel", 1
        )  # there should be one clinical indication-panel link

        errors += value_check_wrapper(
            links[0].pending, "clinical indication-panel pending", False
        )  # created link should not be flagged

        errors += value_check_wrapper(
            links[0].clinical_indication,
            "clinical indication-panel ci",
            self.first_clinical_indication,
        )  # created link should be linked to the setup clinical indication above

        errors += value_check_wrapper(
            links[0].panel,
            "clinical indication-panel panel",
            panels[0],
        )  # created link should be linked to the panel above

        errors += len_check_wrapper(
            ClinicalIndicationPanelHistory.objects.all(),
            "clinical indication-panel history",
            1,
        )  # there should be one record of clinical indication-panel history

        genes = Gene.objects.all()

        errors += len_check_wrapper(
            genes, "gene", 2
        )  # there should be 2 genes created HGNC:1 and HGNC:2

        panel_genes = PanelGene.objects.all()

        errors += len_check_wrapper(
            panel_genes, "panel-gene", 2
        )  # there should be 2 panel-genes relationship

        errors += value_check_wrapper(
            panel_genes[0].panel, "panel-gene panel", panel_genes[1].panel
        )

        assert not errors, errors

    def test_that_previous_clinical_indication_panel_links_are_flagged(self):
        """
        scenario where a new list of hgncs is given to a clinical indication
        that is already in the db

        example:
            clinical indication R123
            is linked to panel HGNC:1,HGNC:2
            the new seed have HGNC:1,HGNC:2,HGNC:3

            we expect the function to make the new link between R123 and HGNC:1,HGNC:2,HGNC:3
            then flag both links (old and new) for review
        """
        errors = []

        first_panel = Panel.objects.create(
            panel_name="HGNC:1,HGNC:2",
            panel_source="test directory",
            test_directory=True,
        )

        ClinicalIndicationPanel.objects.create(
            config_source="230401_RD",
            td_version=sortable_version("5.0"),
            clinical_indication=self.first_clinical_indication,
            panel_id=first_panel.id,
            current=True,
            pending=False,
        )  # we make a mock link in the database with td version 6.1

        mock_test_directory = {
            "td_source": "rare-and-inherited-disease-national-gnomic-test-directory-v5.1.xlsx",
            "config_source": "230401_RD",
            "date": "230616",
        }  # this is the test directory that we are going to seed into the db: td version 5.1

        _make_panels_from_hgncs(
            mock_test_directory,
            self.first_clinical_indication,
            ["HGNC:1", "HGNC:2", "HGNC:3"],
        )

        errors += value_check_wrapper(
            Panel.objects.all(), "panels", 2
        )  # should have 2 panels

        clinical_indication_panels = ClinicalIndicationPanel.objects.all()

        errors += value_check_wrapper(
            clinical_indication_panels, "links", 2
        )  # should have 2 links too

        errors += value_check_wrapper(
            all([link.pending for link in clinical_indication_panels]),
            "both links should be flagged for review",
            True,
        )  # both links should be flagged for review)

        errors += value_check_wrapper(
            clinical_indication_panels[1].td_version,
            "td version",
            sortable_version("5.1"),
        )

        errors += value_check_wrapper(
            clinical_indication_panels[1].config_source, "config source", "230401_RD"
        )

        errors += len_check_wrapper(
            PanelGeneHistory.objects.all(), "panel-gene history records", 3
        )  # should have 3 history recorded HGNC:1 HGNC:2 and HGNC:3

    # NOTE: there is no need to test backward deactivation for panel-gene in this function
    # because it makes panel based on the provided hgncs
    # meaning if there's a change in hgncs, a new panel will always be created and
    # the clinical indication will be linked to it (and both old and new will be flagged for review)
    # this is different from the panel-gene interaction where panel get their genes from PanelApp API
    # thus there's a need to monitor the changes in panel-gene relationship

    def test_long_hgnc_list(self):
        """
        scenario where there's a long list of hgncs and db limit for CharField
        is only 255 chars thus there is a need to limit panel name to 200 chars
        if length exceed 255

        we expect the function to truncate the panel name to 200 chars and store it in db
        """
        mock_test_directory = {
            "td_source": "rare-and-inherited-disease-national-gnomic-test-directory-v5.2.xlsx",
            "config_source": "230401_RD",
            "date": "230616",
        }

        hgncs = [f"HGNC:{i}" for i in range(1000)]

        _make_panels_from_hgncs(
            mock_test_directory, self.first_clinical_indication, hgncs
        )

        panel = Panel.objects.first()

        assert len(panel.panel_name) == 254  # assert that panel name length is 200
