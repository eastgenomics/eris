from django.test import TestCase
from requests_app.models import (
    ClinicalIndication,
    Panel,
    ClinicalIndicationPanel,
    TestDirectoryRelease,
    CiPanelTdRelease,
)

from requests_app.management.commands._insert_panel import (
    _get_most_recent_td_release_for_ci_panel,
)


class TestMostRecentRelease_Panels_MultiEntries(TestCase):
    """
    CASE: Two test directory releases are in the database.
    EXPECT: The most recent release connected to a specific Panel is retrieved,
    as a TestDirectoryRelease object.
    """

    def setUp(self) -> None:
        self.first_release = TestDirectoryRelease.objects.create(release="1.0.0")
        self.second_release = TestDirectoryRelease.objects.create(release="1.0.3")

        self.panel = Panel.objects.create(
            external_id="test",
            panel_name="test panel",
            panel_source="PanelApp",
            panel_version="5",
        )

        self.ci = ClinicalIndication.objects.create(
            r_code="R1", name="some ci", test_method="ngs"
        )

        self.ci_panel = ClinicalIndicationPanel.objects.create(
            clinical_indication=self.ci, panel=self.panel, current=True
        )

        self.ci_panel_td = CiPanelTdRelease.objects.create(
            ci_panel=self.ci_panel, td_release=self.first_release
        )

        self.ci_panel_td_two = CiPanelTdRelease.objects.create(
            ci_panel=self.ci_panel, td_release=self.second_release
        )

    def test_two_entries(self):
        answer = _get_most_recent_td_release_for_ci_panel(self.ci_panel)
        assert answer.release == "1.0.3"


class TestMostRecentRelease_Panels_NoEntries(TestCase):
    """
    CASE: No test directory releases are connected to a Panel in the database.
    EXPECT: None is returned instead of a TestDirectoryRelease.
    """

    def setUp(self) -> None:
        self.first_release = TestDirectoryRelease.objects.create(release="1.0.0")
        self.second_release = TestDirectoryRelease.objects.create(release="1.0.3")

        self.panel = Panel.objects.create(
            external_id="test",
            panel_name="test panel",
            panel_source="PanelApp",
            panel_version="5",
        )

        self.ci = ClinicalIndication.objects.create(
            r_code="R1", name="some ci", test_method="ngs"
        )

        self.ci_panel = ClinicalIndicationPanel.objects.create(
            clinical_indication=self.ci, panel=self.panel, current=True
        )

    def test_no_connected_entries(self):
        answer = _get_most_recent_td_release_for_ci_panel(self.ci_panel)
        assert not answer
