from django.test import TestCase
from panels_backend.models import (
    ClinicalIndication,
    SuperPanel,
    ClinicalIndicationSuperPanel,
    TestDirectoryRelease,
    CiSuperpanelTdRelease,
)

from panels_backend.management.commands._insert_panel import (
    _get_most_recent_td_release_for_ci_superpanel,
)


class TestMostRecentRelease_Superpanels_MultiEntries(TestCase):
    """
    CASE: Two test directory releases are in the database.
    EXPECT: The most recent release connected to a specific SuperPanel is retrieved,
    as a TestDirectoryRelease object.
    """

    def setUp(self) -> None:
        self.first_release = TestDirectoryRelease.objects.create(release="1.0.0")
        self.second_release = TestDirectoryRelease.objects.create(release="1.0.3")

        self.superpanel = SuperPanel.objects.create(
            external_id="test",
            panel_name="test panel",
            panel_source="PanelApp",
            panel_version="5",
        )

        self.ci = ClinicalIndication.objects.create(
            r_code="R1", name="some ci", test_method="ngs"
        )

        self.ci_superpanel = ClinicalIndicationSuperPanel.objects.create(
            clinical_indication=self.ci, superpanel=self.superpanel, current=True
        )

        self.ci_panel_td = CiSuperpanelTdRelease.objects.create(
            ci_superpanel=self.ci_superpanel, td_release=self.first_release
        )

        self.ci_panel_td_two = CiSuperpanelTdRelease.objects.create(
            ci_superpanel=self.ci_superpanel, td_release=self.second_release
        )

    def test_two_entries(self):
        answer = _get_most_recent_td_release_for_ci_superpanel(self.ci_superpanel)
        assert answer.release == "1.0.3"


class TestMostRecentRelease_SuperPanels_NoEntries(TestCase):
    """
    CASE: No test directory releases are connected to a SuperPanel in the database.
    EXPECT: None is returned instead of a TestDirectoryRelease.
    """

    def setUp(self) -> None:
        self.first_release = TestDirectoryRelease.objects.create(release="1.0.0")
        self.second_release = TestDirectoryRelease.objects.create(release="1.0.3")

        self.superpanel = SuperPanel.objects.create(
            external_id="test",
            panel_name="test panel",
            panel_source="PanelApp",
            panel_version="5",
        )

        self.ci = ClinicalIndication.objects.create(
            r_code="R1", name="some ci", test_method="ngs"
        )

        self.ci_superpanel = ClinicalIndicationSuperPanel.objects.create(
            clinical_indication=self.ci, superpanel=self.superpanel, current=True
        )

    def test_no_connected_entries(self):
        answer = _get_most_recent_td_release_for_ci_superpanel(self.ci_superpanel)
        assert not answer
