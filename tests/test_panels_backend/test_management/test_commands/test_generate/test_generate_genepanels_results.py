from django.test import TestCase
from unittest import mock
from unittest.mock import patch, mock_open
from datetime import date

from panels_backend.models import (
    ReferenceGenome,
    TestDirectoryRelease,
    Panel,
    SuperPanel,
    Gene,
    ClinicalIndication,
    ClinicalIndicationPanel,
    ClinicalIndicationSuperPanel,
    CiPanelTdRelease,
    CiSuperpanelTdRelease
)
from panels_backend.management.commands.generate import (
    Command,
)


class TestGenerateGenepanels(TestCase):
    """
    _generate_genepanels_results is primarily a controller function,
    but we want to test for the following behaviours:
    - It gets the most recent TD from several options
    - It gets both Panel and SuperPanel data, formatted correctly
    - It sorts Panels and SuperPanels together based on first 3 cols (note R
    numbers may be imperfect)
    - It excludes specific HGNCs if provided with some
    """
    def setUp(self) -> None:
        # Need multiple TdReleases
        self.td_release_old = TestDirectoryRelease.objects.create(
            release="3",
            td_source="old source",
            config_source="config source",
            td_date="2022-01-01"
        )
        self.td_release_new = TestDirectoryRelease.objects.create(
            release="4",
            td_source="new source",
            config_source="config source",
            td_date="2023-01-01"
        )

        # Clinical Indications
        self.ci_1 = ClinicalIndication.objects.create(
            r_code="R1",
            name="Common condition 1",
            test_method="wgs"
        )
        self.ci_2 = ClinicalIndication.objects.create(
            r_code="R2",
            name="Common condition 2",
            test_method="wgs"
        )
        self.ci_3 = ClinicalIndication.objects.create(
            r_code="R3",
            name="Common condition 3",
            test_method="wgs"
        )

        # Muliple panels and superpanels
        self.panel_1 = Panel.objects.create(
            external_id="20",
            panel_name="Test panel 1",
            panel_source="Test",
            version="4",
            test_directory=True
        )

        self.panel_2 = Panel.objects.create(
            external_id="25",
            panel_name="Test panel 2",
            panel_source="Test",
            version="6",
            test_directory=True
        )

        self.superpanel_1 = SuperPanel.objects.create(
            external_id="10",
            panel_name="A superpanel",
            panel_source="Test",
            version="7",
            test_directory=True
        )

        # the panels and superpanels are each associated with a clinical
        # indication
        self.cip_1 = ClinicalIndicationPanel.objects.create(
            clinical_indication=self.ci_1,
            panel=self.panel_1
        )

        self.cip_2 = ClinicalIndicationPanel.objects.create(
            clinical_indication=self.ci_2,
            panel=self.panel_2
        )

        self.cisp_1 = ClinicalIndicationSuperPanel.objects.create(
            clinical_indication=self.ci_3,
            panel=self.superpanel_1
        )

        # Genes are linked to the panels and superpanels (they may overlap
        # but not necessarily)
        self.gene_1 = Gene.objects.create(
            hgnc_id="HGNC:001",
            gene_symbol="YFG1"
        )
        self.gene_2 = Gene.objects.create(
            hgnc_id="HGNC:002",
            gene_symbol="YFG2"
        )
        self.gene_3 = Gene.objects.create(
            hgnc_id="HGNC:003",
            gene_symbol="YFG3"
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