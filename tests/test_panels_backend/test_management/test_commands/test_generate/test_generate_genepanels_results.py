from django.test import TestCase

from panels_backend.models import (
    TestDirectoryRelease,
    Panel,
    PanelGene,
    SuperPanel,
    PanelSuperPanel,
    Gene,
    ClinicalIndication,
    ClinicalIndicationPanel,
    ClinicalIndicationSuperPanel,
    CiPanelTdRelease,
    CiSuperpanelTdRelease,
)
from panels_backend.management.commands.generate import (
    Command,
)


class TestGenerateGenepanels_TwoTD(TestCase):
    """
    _generate_genepanels_results is primarily a controller function,
    but we want to test for the following behaviours:
    - It gets the most recent TD from several options
    - It gets both Panel and SuperPanel data, and they are formatted correctly
    - It sorts Panels and SuperPanels together based on first 3 cols (note - R
    numbers may be imperfect)
    - It excludes specific HGNCs, if provided with a list
    """

    def setUp(self) -> None:
        # Need multiple TdReleases
        self.td_release_old = TestDirectoryRelease.objects.create(
            release="3",
            td_source="old source",
            config_source="config source",
            td_date="2022-01-01",
        )
        self.td_release_new = TestDirectoryRelease.objects.create(
            release="4",
            td_source="new source",
            config_source="config source",
            td_date="2023-01-01",
        )

        # Clinical Indications
        self.ci_1 = ClinicalIndication.objects.create(
            r_code="R1", name="Common condition 1", test_method="wgs"
        )
        self.ci_2 = ClinicalIndication.objects.create(
            r_code="R2", name="Common condition 2", test_method="wgs"
        )
        self.ci_3 = ClinicalIndication.objects.create(
            r_code="R3", name="Common condition 3", test_method="wgs"
        )

        # Muliple panels and superpanels
        self.panel_1 = Panel.objects.create(
            external_id="20",
            panel_name="Test panel 1",
            panel_source="Test",
            panel_version="4",
            test_directory=True,
        )

        self.panel_2 = Panel.objects.create(
            external_id="25",
            panel_name="Test panel 2",
            panel_source="Test",
            panel_version="6",
            test_directory=True,
        )

        self.superpanel_1 = SuperPanel.objects.create(
            external_id="10",
            panel_name="A superpanel",
            panel_source="Test",
            panel_version="7",
            test_directory=True,
        )

        # the panels and superpanels are each associated with a clinical
        # indication
        self.cip_1 = ClinicalIndicationPanel.objects.create(
            clinical_indication=self.ci_1, panel=self.panel_1, current=True
        )

        self.cip_2 = ClinicalIndicationPanel.objects.create(
            clinical_indication=self.ci_2, panel=self.panel_2, current=True
        )

        self.cisp_1 = ClinicalIndicationSuperPanel.objects.create(
            clinical_indication=self.ci_3,
            superpanel=self.superpanel_1,
            current=True,
        )

        # Genes are linked to the panels and superpanels (they may overlap
        # but not necessarily)
        self.gene_1 = Gene.objects.create(
            hgnc_id="HGNC:001", gene_symbol="YFG1"
        )
        self.panel_1_gene_1 = PanelGene.objects.create(
            panel=self.panel_1, gene=self.gene_1, active=True
        )

        self.gene_2 = Gene.objects.create(
            hgnc_id="HGNC:002", gene_symbol="YFG2"
        )
        self.panel_2_gene_1 = PanelGene.objects.create(
            panel=self.panel_2, gene=self.gene_1, active=True
        )

        self.gene_3 = Gene.objects.create(
            hgnc_id="HGNC:003", gene_symbol="YFG3"
        )

        # finally, Ci-Panel or Ci-SuperPanel associations may
        # exist in some TD releases, but not others
        self.cip_td_old_1 = CiPanelTdRelease.objects.create(
            ci_panel=self.cip_1,
            td_release=self.td_release_old,
        )

        self.cip_td_new_1 = CiPanelTdRelease.objects.create(
            ci_panel=self.cip_1,
            td_release=self.td_release_new,
        )

        self.cip_td_old_2 = CiPanelTdRelease.objects.create(
            ci_panel=self.cip_2,
            td_release=self.td_release_old,
        )

        self.cisp_td_new_1 = CiSuperpanelTdRelease.objects.create(
            ci_superpanel=self.cisp_1,
            td_release=self.td_release_new,
        )

        # We need to link CiSuperpanel to some child-panels which have gene
        # links - otherwise there won't be any Superpanel data to return
        self.child_panel_1 = Panel.objects.create(
            external_id="300",
            panel_name="Child panel 1",
            panel_source="Test",
            panel_version="4",
            test_directory=True,
        )

        self.child_gene_1 = Gene.objects.create(
            hgnc_id="HGNC:010", gene_symbol="YFG10"
        )
        _ = PanelGene.objects.create(
            panel=self.child_panel_1, gene=self.child_gene_1, active=True
        )

        self.child_gene_2 = Gene.objects.create(
            hgnc_id="HGNC:011", gene_symbol="YFG11"
        )
        self.panel_2_gene_1 = PanelGene.objects.create(
            panel=self.child_panel_1, gene=self.child_gene_2, active=True
        )

        self.child_panel_2 = Panel.objects.create(
            external_id="301",
            panel_name="Child panel 2",
            panel_source="Test",
            panel_version="4",
            test_directory=True,
        )

        _ = PanelSuperPanel.objects.create(
            panel=self.child_panel_1, superpanel=self.superpanel_1
        )

        _ = PanelSuperPanel.objects.create(
            panel=self.child_panel_2, superpanel=self.superpanel_1
        )

    def test_no_hgnc_exclusion(self):
        """
        CASE: Request genepanels for most-recent test directory.
        EXPECT: Genepanels which are only linked to NEW TDs, are
        included in the output file. This includes genes linked to
        child-panels of any active, new-TD superpanels
        """
        cmd = Command()

        excluded_hgnc = []
        results = cmd._generate_genepanels_results(excluded_hgnc)

        # Note that superpanel-derived rows get the superpanel names and IDs,
        # rather than the names and IDs of the child-panels
        expected = [
            ["R1_Common condition 1", "Test panel 1_4.0", "HGNC:001", "20"],
            ["R3_Common condition 3", "A superpanel_7.0", "HGNC:010", "10"],
            ["R3_Common condition 3", "A superpanel_7.0", "HGNC:011", "10"],
        ]
        self.assertEqual(expected, results)

    def test_with_hgnc_exclusion(self):
        """
        CASE: Request genepanels for most-recent test directory. Specify
        unwanted HGNC gene IDs.
        EXPECT: Genepanels which are only linked to NEW TDs, are
        included in the output file. This includes genes linked to
        child-panels of any active, new-TD superpanels.
        A row is missing because we exclude HGNC:010
        """
        cmd = Command()

        excluded_hgnc = ["HGNC:010"]
        results = cmd._generate_genepanels_results(excluded_hgnc)

        expected = [
            ["R1_Common condition 1", "Test panel 1_4.0", "HGNC:001", "20"],
            ["R3_Common condition 3", "A superpanel_7.0", "HGNC:011", "10"],
        ]
        self.assertEqual(expected, results)
