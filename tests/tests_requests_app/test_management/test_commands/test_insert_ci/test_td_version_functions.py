from django.test import TestCase

from requests_app.models import (
    PanelGene,
    Panel,
    SuperPanel,
    ClinicalIndication,
    ClinicalIndicationPanel,
    ClinicalIndicationSuperPanel
)
from requests_app.management.commands._insert_ci import _fetch_latest_td_version
from requests_app.management.commands.utils import sortable_version
from tests.tests_requests_app.test_management.test_commands.test_insert_panel.test_insert_gene import (
    len_check_wrapper,
    value_check_wrapper,
)


class TestFetchLatestTdVersion_OlderPanel(TestCase):
    """
    Check that when the latest td version is in the Panel,
    the data is correctly returned
    EXPECT: ClinicalIndicationPanel's td version is returned as correct
    """
    def setUp(self) -> None:
        self.ci = ClinicalIndication.objects.create(r_code="R100.1",
                           name="An illness",
                           test_method="NGS"
                           )

        self.panel = Panel.objects.create(
            external_id=500,
            panel_source="PanelApp",
            panel_version=6
        )

        self.superpanel= SuperPanel.objects.create(
            external_id=500,
            panel_source="PanelApp",
            panel_version=6
        )

        self.ci_panel = ClinicalIndicationPanel.objects.create(
            config_source="test",
            td_version="3",
            clinical_indication=self.ci,
            panel=self.panel,
            current=True
        )

        self.ci_superpanel = ClinicalIndicationSuperPanel.objects.create(
            config_source="test",
            td_version="2",
            clinical_indication=self.ci,
            superpanel=self.superpanel,
            current=True
        )
    
    def test_panel_older_than_superpanel(self):
        """
        Check that when the latest td version is in the Panel,
        the data is correctly returned
        EXPECT: ClinicalIndicationPanel's td version is returned as correct
        """
        latest_td = _fetch_latest_td_version()

        assert latest_td == sortable_version("3")


class TestFetchLatestTdVersion_OlderSuperPanel(TestCase):
    """
    Check that when the latest td version is in the SuperPanel,
    the data is correctly returned
    EXPECT: ClinicalIndicationSuperPanel's td version is returned as correct
    """
    def setUp(self) -> None:
        self.ci = ClinicalIndication.objects.create(r_code="R100.1",
                           name="An illness",
                           test_method="NGS"
                           )

        self.panel = Panel.objects.create(
            external_id=500,
            panel_source="PanelApp",
            panel_version=6
        )

        self.superpanel= SuperPanel.objects.create(
            external_id=500,
            panel_source="PanelApp",
            panel_version=6
        )

        self.ci_panel = ClinicalIndicationPanel.objects.create(
            config_source="test",
            td_version="3",
            clinical_indication=self.ci,
            panel=self.panel,
            current=True
        )

        self.ci_superpanel = ClinicalIndicationSuperPanel.objects.create(
            config_source="test",
            td_version="4",
            clinical_indication=self.ci,
            superpanel=self.superpanel,
            current=True
        )
    
    def test_superpanel_older_than_panel(self):
        """
        Check that when the latest td version is in the SuperPanel,
        the data is correctly returned
        EXPECT: ClinicalIndicationSuperPanel's td version is returned as correct
        """
        latest_td = _fetch_latest_td_version()

        assert latest_td == sortable_version("4")


class TestFetchLatestTdVersion_PanelOnly(TestCase):
    """
    Check that when there is no SuperPanel data in the db,
    the td version in the panel-related data is correctly returned
    EXPECT: ClinicalIndicationPanel's td version is returned as correct
    """
    def setUp(self) -> None:
        self.ci = ClinicalIndication.objects.create(r_code="R100.1",
                           name="An illness",
                           test_method="NGS"
                           )

        self.panel = Panel.objects.create(
            external_id=500,
            panel_source="PanelApp",
            panel_version=6
        )

        self.ci_panel = ClinicalIndicationPanel.objects.create(
            config_source="test",
            td_version="3",
            clinical_indication=self.ci,
            panel=self.panel,
            current=True
        )
    
    def test_only_panel_exists(self):
        """
        Check that when there is no SuperPanel data in the db,
        the td version in the panel-related data is correctly returned
        EXPECT: ClinicalIndicationPanel's td version is returned as correct
        """
        latest_td = _fetch_latest_td_version()

        assert latest_td == sortable_version("3")


class TestFetchLatestTdVersion_SuperPanelOnly(TestCase):
    """
    Check that when there is no Panel data in the db,
    the td version in the panel-related data is correctly returned
    EXPECT: ClinicalIndicationSuperPanel's td version is returned as correct
    """
    def setUp(self) -> None:
        self.ci = ClinicalIndication.objects.create(r_code="R100.1",
                           name="An illness",
                           test_method="NGS"
                           )

        self.panel = SuperPanel.objects.create(
            external_id=500,
            panel_source="PanelApp",
            panel_version=6
        )

        self.ci_panel = ClinicalIndicationSuperPanel.objects.create(
            config_source="test",
            td_version="3",
            clinical_indication=self.ci,
            superpanel=self.panel,
            current=True
        )
    
    def test_only_panel_exists(self):
        """
        Check that when there is no Panel data in the db,
        the td version in the panel-related data is correctly returned
        EXPECT: ClinicalIndicationSuperPanel's td version is returned as correct
        """
        latest_td = _fetch_latest_td_version()

        assert latest_td == sortable_version("3")


class TestFetchLatestTdVersion_NoDataAvailable(TestCase):
    """
    Check that when there is no data in the db for panels or superpanels,
    a None value is returned
    EXPECT: td version returns as None
    """
    def setUp(self) -> None:
        pass
    
    def test_only_panel_exists(self):
        latest_td = _fetch_latest_td_version()

        assert latest_td == None