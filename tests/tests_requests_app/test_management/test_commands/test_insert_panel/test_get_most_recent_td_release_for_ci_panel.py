from django.test import TestCase
from requests_app.models import (
    ClinicalIndication,
    Panel,
    SuperPanel,
    ClinicalIndicationPanel,
    ClinicalIndicationSuperPanel,
    TestDirectoryRelease,
    CiPanelTdRelease
)
from requests_app.management.commands.utils import sortable_version
from requests_app.management.commands._insert_panel import (
    _get_most_recent_td_release_for_ci_panel
)


class TestMostRecentRelease(TestCase):
    """
    """
    def setUp(self) -> None:
        self.first_release = TestDirectoryRelease(release="1.0.0")
        
        self.panel = Panel(
            external_id="test",
            panel_name="test panel",
            panel_source="PanelApp",
            panel_version="5"
        )

        self.ci = ClinicalIndication(
            r_code="R1",
            name="some ci",
            test_method="ngs"
        )

        self.ci_panel = ClinicalIndicationPanel(
            clinical_indication=self.ci,
            panel=self.panel
        )

        self.ci_panel_td = CiPanelTdRelease(
            ci_panel=self.ci_panel,
            td_release=self.first_release
        )

    def test_single_entry(self):
        ans = _get_most_recent_td_release_for_ci_panel(self.ci_panel)
        assert ans == "1.0.0"
    