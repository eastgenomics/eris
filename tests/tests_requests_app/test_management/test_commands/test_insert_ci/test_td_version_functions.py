from django.test import TestCase

from requests_app.models import (
    PanelGene,
    Panel,
    SuperPanel,
    ClinicalIndication,
    ClinicalIndicationPanel,
    ClinicalIndicationSuperPanel,
    TestDirectoryRelease,
    CiPanelTdRelease,
    CiSuperpanelTdRelease
)
from requests_app.management.commands._insert_ci import _fetch_latest_td_version
from requests_app.management.commands.utils import sortable_version


class TestFetchLatestTdVersion_OlderPanel(TestCase):
    """
    Check that when the latest td version is in the Panel,
    the data is correctly returned
    EXPECT: ClinicalIndicationPanel's td version is returned as correct
    """

    def setUp(self) -> None:
        self.td_release = TestDirectoryRelease.objects.create(
            release="2"
        )

        self.td_release_two = TestDirectoryRelease.objects.create(
            release="3"
        )

        self.ci = ClinicalIndication.objects.create(
            r_code="R100.1", name="An illness", test_method="NGS"
        )

        self.panel = Panel.objects.create(
            external_id=500, panel_source="PanelApp", panel_version=6
        )

        self.superpanel = SuperPanel.objects.create(
            external_id=500, panel_source="PanelApp", panel_version=6
        )

        self.ci_panel = ClinicalIndicationPanel.objects.create(
            config_source="test",
            clinical_indication=self.ci,
            panel=self.panel,
            current=True,
        )

        self.ci_superpanel = ClinicalIndicationSuperPanel.objects.create(
            config_source="test",
            clinical_indication=self.ci,
            superpanel=self.superpanel,
            current=True,
        )

        self.cip_td = CiPanelTdRelease(
            ci_panel=self.ci_panel,
            td_release=self.td_release
        )

        self.cip_td = CiSuperpanelTdRelease(
            ci_superpanel=self.ci_superpanel,
            td_release=self.td_release_two
        )

    def test_panel_older_than_superpanel(self):
        """
        Check that when the latest td version is in the Panel,
        the data is correctly returned
        EXPECT: ClinicalIndicationPanel's td version is returned as correct
        """
        latest_td = _fetch_latest_td_version()

        assert latest_td == "3"


class TestFetchLatestTdVersion_OlderSuperPanel(TestCase):
    """
    Check that when the latest td version is in the SuperPanel,
    the data is correctly returned
    EXPECT: ClinicalIndicationSuperPanel's td version is returned as correct
    """

    def setUp(self) -> None:
        self.ci = ClinicalIndication.objects.create(
            r_code="R100.1", name="An illness", test_method="NGS"
        )

        self.panel = Panel.objects.create(
            external_id=500, panel_source="PanelApp", panel_version=6
        )

        self.superpanel = SuperPanel.objects.create(
            external_id=500, panel_source="PanelApp", panel_version=6
        )

        self.td_old = TestDirectoryRelease.objects.create(release="3")
        self.td_new = TestDirectoryRelease.objects.create(release="4")

        self.ci_panel = ClinicalIndicationPanel.objects.create(
            config_source="test",
            clinical_indication=self.ci,
            panel=self.panel,
            current=True,
        )

        self.ci_panel_td_release = CiPanelTdRelease(
            ci_panel=self.ci_panel,
            td_release=self.td_old
        )

        self.ci_superpanel = ClinicalIndicationSuperPanel.objects.create(
            config_source="test",
            clinical_indication=self.ci,
            superpanel=self.superpanel,
            current=True,
        )

        self.ci_superpanel_td_release = CiSuperpanelTdRelease(
            ci_superpanel=self.ci_superpanel,
            td_release=self.td_new
        )

    def test_superpanel_older_than_panel(self):
        """
        Check that when the latest td version is in the SuperPanel,
        the data is correctly returned
        EXPECT: ClinicalIndicationSuperPanel's td version is returned as correct
        """
        latest_td = _fetch_latest_td_version()

        assert latest_td == "4"


class TestFetchLatestTdVersion_PanelOnly(TestCase):
    """
    Check that when there is no SuperPanel data in the db,
    the td version in the panel-related data is correctly returned
    EXPECT: ClinicalIndicationPanel's td version is returned as correct
    """

    def setUp(self) -> None:
        self.ci = ClinicalIndication.objects.create(
            r_code="R100.1", name="An illness", test_method="NGS"
        )

        self.panel = Panel.objects.create(
            external_id=500, panel_source="PanelApp", panel_version=6
        )

        self.ci_panel = ClinicalIndicationPanel.objects.create(
            config_source="test",
            clinical_indication=self.ci,
            panel=self.panel,
            current=True,
        )

        self.td = TestDirectoryRelease.objects.create(release="3")

        self.ci_panel_td = CiPanelTdRelease(ci_panel=self.ci_panel,
                                            td_release=self.td)


    def test_only_panel_exists(self):
        """
        Check that when there is no SuperPanel data in the db,
        the td version in the panel-related data is correctly returned
        EXPECT: ClinicalIndicationPanel's td version is returned as correct
        """
        latest_td = _fetch_latest_td_version()

        assert latest_td == "3"


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

        assert not latest_td


# TODO: test '_check_td_version_valid' if concerned
