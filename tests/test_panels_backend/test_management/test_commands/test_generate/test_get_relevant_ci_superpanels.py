from django.test import TestCase
import collections

from panels_backend.models import (
    SuperPanel,
    ClinicalIndication,
    ClinicalIndicationSuperPanel,
    TestDirectoryRelease,
    CiSuperpanelTdRelease,
)
from panels_backend.management.commands.generate import Command


class TestGetRelevantCiSuperPanels_Basic(TestCase):
    def setUp(self) -> None:
        self.panel_1 = SuperPanel.objects.create(
            external_id="109",
            panel_name="First Panel",
            panel_version="5",
            test_directory=True,
            custom=False,
            pending=False,
        )
        self.panel_2 = SuperPanel.objects.create(
            external_id="209",
            panel_name="Second Panel",
            panel_version="2",
            test_directory=True,
            custom=False,
            pending=False,
        )

        self.ci_1 = ClinicalIndication.objects.create(
            r_code="R1", name="Condition 1", test_method="NGS", pending=False
        )
        self.ci_2 = ClinicalIndication.objects.create(
            r_code="R2", name="Condition 2", test_method="NGS", pending=False
        )

        self.cip_1 = ClinicalIndicationSuperPanel.objects.create(
            clinical_indication=self.ci_1,
            superpanel=self.panel_1,
            current=True,
            pending=False,
        )
        self.cip_2 = ClinicalIndicationSuperPanel.objects.create(
            clinical_indication=self.ci_2,
            superpanel=self.panel_2,
            current=True,
            pending=False,
        )

        self.td_release = TestDirectoryRelease.objects.create(
            release="5",
            td_source="a_file.xlsx",
            config_source="config",
            td_date="20231208",
        )

        CiSuperpanelTdRelease.objects.create(
            ci_superpanel=self.cip_1, td_release=self.td_release
        )
        CiSuperpanelTdRelease.objects.create(
            ci_superpanel=self.cip_2, td_release=self.td_release
        )

    def test_get_relevant_ci_superpanels_basic(self):
        """
        CASE: A test directory release is linked to 2 CI-SuperPanels
        EXPECT: We get a 'ci_superpanels' dictionary linking R codes to every ci-superpanel,
        and a 'relevant superpanels' set of the superpanels' names
        """
        cmd = Command()
        ci_superpanels, relevant_superpanels = cmd._get_relevant_ci_superpanels(
            self.td_release
        )

        expected_ci_superpanels = {
            "R1": [
                {
                    "ci_superpanel__clinical_indication__r_code": "R1",
                    "ci_superpanel__clinical_indication__name": "Condition 1",
                    "ci_superpanel__superpanel": self.panel_1.id,
                    "ci_superpanel__superpanel__external_id": "109",
                    "ci_superpanel__superpanel__panel_name": "First Panel",
                    "ci_superpanel__superpanel__panel_version": "5",
                }
            ],
            "R2": [
                {
                    "ci_superpanel__clinical_indication__r_code": "R2",
                    "ci_superpanel__clinical_indication__name": "Condition 2",
                    "ci_superpanel__superpanel": self.panel_2.id,
                    "ci_superpanel__superpanel__external_id": "209",
                    "ci_superpanel__superpanel__panel_name": "Second Panel",
                    "ci_superpanel__superpanel__panel_version": "2",
                }
            ],
        }

        expected_rel_superpanels = set([self.panel_1.id, self.panel_2.id])

        self.maxDiff = None
        self.assertEqual(expected_rel_superpanels, relevant_superpanels)
        self.assertDictEqual(expected_ci_superpanels, ci_superpanels)

    def test_get_relevant_ci_panels_ignore_pending_not_current(self):
        """
        CASE: A test directory release is linked to 2 current, not-pending CI-SuperPanels.
        It is also linked to a non-current CI-SuperPanel and a pending CI-SuperPanel.
        EXPECT: We get results only for the current not-pending CI-SuperPanels.
        """
        # Set up an old and pending Ci-SuperPanel - in addition to the current/not-pending ones
        # in setUp

        self.panel_old = SuperPanel.objects.create(
            external_id="309",
            panel_name="Third Panel",
            panel_version="2",
            test_directory=True,
            custom=False,
            pending=False,
        )

        self.cip_3 = ClinicalIndicationSuperPanel.objects.create(
            clinical_indication=self.ci_1,
            superpanel=self.panel_old,
            current=False,
            pending=False,
        )

        self.panel_link_pending = SuperPanel.objects.create(
            external_id="409",
            panel_name="Fourth Panel",
            panel_version="2",
            test_directory=True,
            custom=False,
            pending=True,
        )

        self.cip_4 = ClinicalIndicationSuperPanel.objects.create(
            clinical_indication=self.ci_1,
            superpanel=self.panel_link_pending,
            current=False,
            pending=True,
        )

        cmd = Command()
        ci_superpanels, relevant_superpanels = cmd._get_relevant_ci_superpanels(
            self.td_release
        )

        expected_ci_superpanels = {
            "R1": [
                {
                    "ci_superpanel__clinical_indication__r_code": "R1",
                    "ci_superpanel__clinical_indication__name": "Condition 1",
                    "ci_superpanel__superpanel": self.panel_1.id,
                    "ci_superpanel__superpanel__external_id": "109",
                    "ci_superpanel__superpanel__panel_name": "First Panel",
                    "ci_superpanel__superpanel__panel_version": "5",
                }
            ],
            "R2": [
                {
                    "ci_superpanel__clinical_indication__r_code": "R2",
                    "ci_superpanel__clinical_indication__name": "Condition 2",
                    "ci_superpanel__superpanel": self.panel_2.id,
                    "ci_superpanel__superpanel__external_id": "209",
                    "ci_superpanel__superpanel__panel_name": "Second Panel",
                    "ci_superpanel__superpanel__panel_version": "2",
                }
            ],
        }

        expected_rel_superpanels = set([self.panel_1.id, self.panel_2.id])

        self.maxDiff = None
        self.assertDictEqual(expected_ci_superpanels, ci_superpanels)
        self.assertEqual(expected_rel_superpanels, relevant_superpanels)
