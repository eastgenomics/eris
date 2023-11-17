from django.test import TestCase

from requests_app.management.commands.history import History
from requests_app.models import (
    ClinicalIndication,
    SuperPanel,
    ClinicalIndicationSuperPanel,
    ClinicalIndicationSuperPanelHistory,
    TestDirectoryRelease,
    CiSuperpanelTdRelease,
    CiSuperpanelTdReleaseHistory,
)
from requests_app.management.commands._insert_ci import _make_ci_superpanel_td_link


class TestMakeCiSuperpanelTdLink_NewCip(TestCase):
    """
    Cases where a CI-SuperPanel link is made for the first time,
    then linked to a new test directory release
    """

    def setUp(self) -> None:
        """
        Make the ClinicalIndication, SuperPanel and TestDirectoryRelease,
        ready for linking
        """
        self.ci = ClinicalIndication.objects.create(
            r_code="R104", name="Clin Ind Here", test_method="ngs"
        )

        self.panel = SuperPanel.objects.create(
            external_id="304",
            panel_name="A class of genetic disorder",
            panel_source="source",
            panel_version="3",
        )

        self.td_release = TestDirectoryRelease.objects.create(
            release="2",
            td_source="test_dir_v2.xlsx",
            config_source="config source",
            td_date="20220405",
        )

        self.user = "test_user"

    def test_superpanel_ci_and_td_link_made(self):
        """
        CASE: a CI-SuperPanel link needs making and doesn't exist already
        EXPECT: CI-SuperPanel are linked with a history entry, then linked to a new test directory release,
        which itself generates a history entry
        """
        cip, cip_created = _make_ci_superpanel_td_link(
            self.ci, self.panel, self.td_release, self.user
        )

        # check the CI-Panel link is made
        with self.subTest():
            assert cip_created
            self.assertEqual(cip.clinical_indication, self.ci)
            self.assertEqual(cip.superpanel, self.panel)

        # check the CI-Panel is linked to the test directory release
        with self.subTest():
            cip_td = CiSuperpanelTdRelease.objects.all()
            assert len(cip_td) == 1
            self.assertEqual(cip_td[0].ci_superpanel, cip)
            self.assertEqual(cip_td[0].td_release, self.td_release)

        # check ci-panel history logs
        with self.subTest():
            cip_hist = ClinicalIndicationSuperPanelHistory.objects.all()
            assert len(cip_hist) == 1
            self.assertEqual(
                cip_hist[0].note, History.clinical_indication_superpanel_created()
            )

        # check cip-td  history logs
        with self.subTest():
            cip_td_hist = CiSuperpanelTdReleaseHistory.objects.all()
            assert len(cip_td_hist) == 1
            self.assertEqual(
                cip_td_hist[0].note,
                History.td_superpanel_ci_autolink(cip_td[0].td_release.release),
            )


class TestMakeCiPanelTdLink_ExistingCip(TestCase):
    """
    Cases where a CI-Panel link already exists,
    then gets linked to a new test directory release
    """

    def setUp(self) -> None:
        """
        Make the ClinicalIndication, Panel and TestDirectoryRelease,
        ready for linking
        """
        self.ci = ClinicalIndication.objects.create(
            r_code="R104", name="Clin Ind Here", test_method="ngs"
        )

        self.panel = SuperPanel.objects.create(
            external_id="304",
            panel_name="A class of genetic disorder",
            panel_source="source",
            panel_version="3",
        )

        self.td_release = TestDirectoryRelease.objects.create(
            release="2",
            td_source="test_dir_v2.xlsx",
            config_source="config source",
            td_date="20220405",
        )

        self.user = "test_user"

        self.cip = ClinicalIndicationSuperPanel.objects.create(
            superpanel=self.panel, clinical_indication=self.ci, current=True
        )

    def test_td_link_made(self):
        """
        CASE: a CI-Panel link is already made, but needs linking to a new td
        EXPECT: CI-Panel is linked to a new test directory release. History log reflects metadata
        change
        """
        new_cip, cip_created = _make_ci_superpanel_td_link(
            self.ci, self.panel, self.td_release, self.user
        )

        # check the CI-Panel link is as expected
        with self.subTest():
            assert not cip_created
            self.assertEqual(new_cip, self.cip)

        # check the CI-Panel is linked to the test directory release
        with self.subTest():
            cip_td = CiSuperpanelTdRelease.objects.all()
            assert len(cip_td) == 1
            self.assertEqual(cip_td[0].ci_superpanel, new_cip)
            self.assertEqual(cip_td[0].td_release, self.td_release)

        # check history logs
        with self.subTest():
            hist = CiSuperpanelTdReleaseHistory.objects.all()
            assert len(hist) == 1
            self.assertEqual(
                hist[0].note,
                History.td_superpanel_ci_autolink(
                    cip_td[0].td_release.release,
                ),
            )
