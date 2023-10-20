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
        latest_td = _fetch_latest_td_version()

        assert latest_td == sortable_version("3")


class TestFetchLatestTdVersion_OlderSuperPanel(TestCase):
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
        latest_td = _fetch_latest_td_version()

        assert latest_td == sortable_version("4")


class TestFetchLatestTdVersion_PanelOnly(TestCase):
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
        latest_td = _fetch_latest_td_version()

        assert latest_td == sortable_version("3")


class TestFetchLatestTdVersion_SuperPanelOnly(TestCase):
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
        latest_td = _fetch_latest_td_version()

        assert latest_td == sortable_version("3")


class TestFetchLatestTdVersion_NoDataAvailable(TestCase):
    def setUp(self) -> None:
        pass
    
    def test_only_panel_exists(self):
        latest_td = _fetch_latest_td_version()

        assert latest_td == None