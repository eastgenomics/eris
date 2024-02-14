"""
This file test the function `_make_panels_from_hgncs` in the file `panels_backend/management/commands/_insert_ci.py`

Tested scenario:
- core function of making panels from a list of hgncs and linking it to a clinical indication
- scenario where a new list of hgncs is given to an existing clinical indication (that is already in the db)
"""

from django.test import TestCase
from django.contrib.auth.models import User

from panels_backend.models import (
    ClinicalIndication,
    Panel,
    ClinicalIndicationPanel,
    Gene,
    PanelGene,
    PanelGeneHistory,
    ClinicalIndicationPanelHistory,
    TestDirectoryRelease,
    CiPanelTdRelease,
)
from panels_backend.management.commands._insert_ci import (
    _make_panels_from_hgncs,
)
from tests.test_panels_backend.test_management.test_commands.test_insert_panel.test_insert_gene import (
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
    if the same clinical indication gets a different panel (different), new link should be generated but
    flagged for review (new and old links)

    """

    def setUp(self) -> None:
        self.first_clinical_indication = ClinicalIndication.objects.create(
            r_code="R123",
            name="Test CI",
            test_method="Test method",
        )

        self.td_version = TestDirectoryRelease.objects.create(
            release="3.0",
            td_source="rare-and-inherited-disease-national-gnomic-test-directory-v5.1.xlsx",
            config_source="230401_RD",
            td_date="230616",
        )

        self.user = User.objects.create_user(username="test", is_staff=True)

    def test_make_panel_function(self):
        """
        Given a list of hgncs, make a panel and link it to the clinical indication
        """
        errors = []

        _make_panels_from_hgncs(
            self.first_clinical_indication,
            self.td_version,
            ["HGNC:1", "HGNC:2"],
            self.user,
        )

        panels = Panel.objects.all()

        errors += len_check_wrapper(panels, "panel", 1)
        errors += value_check_wrapper(
            panels[0].panel_name,
            "panel name",
            "HGNC:1&HGNC:2",
        )  # panel name should be the list of hgncs joined by an ampersand

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
        errors += value_check_wrapper(
            ClinicalIndicationPanelHistory.objects.all()[0].user,
            "history username",
            self.user,
        )

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

        # check that test directory release links are formed
        links_with_td = CiPanelTdRelease.objects.all()
        errors += len_check_wrapper(links_with_td, "links with td", 1)
        errors += value_check_wrapper(
            links_with_td[0].td_release, "td release in link", self.td_version
        )
        errors += value_check_wrapper(
            links_with_td[0].ci_panel, "ci-panel in link", links[0]
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
            clinical_indication=self.first_clinical_indication,
            panel_id=first_panel.id,
            current=True,
            pending=False,
        )  # we make a mock link in the database with td version 6.1

        _make_panels_from_hgncs(
            self.first_clinical_indication,
            self.td_version,
            ["HGNC:1", "HGNC:2", "HGNC:3"],
            self.user,
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

        errors += len_check_wrapper(
            PanelGeneHistory.objects.all(), "panel-gene history records", 3
        )  # should have 3 history recorded HGNC:1 HGNC:2 and HGNC:3

        errors += value_check_wrapper(
            PanelGeneHistory.objects.all()[0].user.username,
            "PanelGeneHistory user",
            "test",
        )

        # check that test directory release links are formed
        links_with_td = CiPanelTdRelease.objects.all()
        errors += len_check_wrapper(links_with_td, "links with td", 2)
        errors += value_check_wrapper(
            links_with_td[0].td_release, "td release in link", self.td_version
        )

    # NOTE: there is no need to test backward deactivation for panel-gene in this function
    # because it makes panel based on the provided hgncs
    # meaning if there's a change in hgncs, a new panel will always be created and
    # the clinical indication will be linked to it (and both old and new will be flagged for review)
    # this is different from the panel-gene interaction where panel get their genes from PanelApp API
    # thus there's a need to monitor the changes in panel-gene relationship
