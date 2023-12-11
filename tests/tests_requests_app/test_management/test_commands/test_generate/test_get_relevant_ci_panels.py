from django.test import TestCase

from requests_app.models import (
    Panel,
    ClinicalIndication,
    ClinicalIndicationPanel,
    TestDirectoryRelease,
    CiPanelTdRelease,
)
from requests_app.management.commands.generate import Command


class TestGetRelevantCiPanels_Basic(TestCase):
    def setUp(self) -> None:
        self.panel_1 = Panel.objects.create(
            external_id="109",
            panel_name="First Panel",
            panel_version="5",
            test_directory=True,
            custom=False,
            pending=False,
        )
        self.panel_2 = Panel.objects.create(
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

        self.cip_1 = ClinicalIndicationPanel.objects.create(
            clinical_indication=self.ci_1,
            panel=self.panel_1,
            current=True,
            pending=False,
        )
        self.cip_2 = ClinicalIndicationPanel.objects.create(
            clinical_indication=self.ci_2,
            panel=self.panel_2,
            current=True,
            pending=False,
        )

        self.td_release = TestDirectoryRelease.objects.create(
            release="5",
            td_source="a_file.xlsx",
            config_source="config",
            td_date="20231208",
        )

        CiPanelTdRelease.objects.create(ci_panel=self.cip_1, td_release=self.td_release)
        CiPanelTdRelease.objects.create(ci_panel=self.cip_2, td_release=self.td_release)

    def test_get_relevant_ci_panels_basic(self):
        """
        CASE: A test directory release is linked to 2 CI-Panels
        EXPECT: We get a 'ci_panels' dictionary linking R codes to every ci-panel,
        and a 'relevant panels' set of the panels' names
        """
        cmd = Command()
        ci_panels, relevant_panels = cmd._get_relevant_ci_panels(self.td_release)

        expected_ci_panels = {
            "R1": [
                {
                    "ci_panel__clinical_indication__r_code": "R1",
                    "ci_panel__clinical_indication_id__name": "Condition 1",
                    "ci_panel__panel_id": self.panel_1.pk,
                    "ci_panel__panel__external_id": "109",
                    "ci_panel__panel__panel_name": "First Panel",
                    "ci_panel__panel__panel_version": "5",
                }
            ],
            "R2": [
                {
                    "ci_panel__clinical_indication__r_code": "R2",
                    "ci_panel__clinical_indication_id__name": "Condition 2",
                    "ci_panel__panel_id": self.panel_2.pk,
                    "ci_panel__panel__external_id": "209",
                    "ci_panel__panel__panel_name": "Second Panel",
                    "ci_panel__panel__panel_version": "2",
                }
            ],
        }

        expected_rel_panels = set([self.panel_1.pk, self.panel_2.pk])

        self.assertEqual(expected_ci_panels, ci_panels)
        self.assertEqual(expected_rel_panels, relevant_panels)

    def test_get_relevant_ci_panels_ignore_pending_not_current(self):
        """
        CASE: A test directory release is linked to 2 current, not-pending CI-Panels.
        It is also linked to a non-current CI-Panel and a pending CI-Panel.
        EXPECT: We get results only for the current not-pending CI-Panels.
        """
        # Set up an old and pending Ci-Panel - in addition to the items defined in setUp

        self.panel_old = Panel.objects.create(
            external_id="309",
            panel_name="Third Panel",
            panel_version="2",
            test_directory=True,
            custom=False,
            pending=False,
        )

        self.cip_3 = ClinicalIndicationPanel.objects.create(
            clinical_indication=self.ci_1,
            panel=self.panel_old,
            current=False,
            pending=False,
        )

        self.panel_link_pending = Panel.objects.create(
            external_id="409",
            panel_name="Fourth Panel",
            panel_version="2",
            test_directory=True,
            custom=False,
            pending=True,
        )

        self.cip_4 = ClinicalIndicationPanel.objects.create(
            clinical_indication=self.ci_1,
            panel=self.panel_link_pending,
            current=False,
            pending=True,
        )

        # Run the test

        cmd = Command()
        ci_panels, relevant_panels = cmd._get_relevant_ci_panels(self.td_release)

        expected_ci_panels = {
            "R1": [
                {
                    "ci_panel__clinical_indication__r_code": "R1",
                    "ci_panel__clinical_indication_id__name": "Condition 1",
                    "ci_panel__panel_id": self.panel_1.pk,
                    "ci_panel__panel__external_id": "109",
                    "ci_panel__panel__panel_name": "First Panel",
                    "ci_panel__panel__panel_version": "5",
                }
            ],
            "R2": [
                {
                    "ci_panel__clinical_indication__r_code": "R2",
                    "ci_panel__clinical_indication_id__name": "Condition 2",
                    "ci_panel__panel_id": self.panel_2.pk,
                    "ci_panel__panel__external_id": "209",
                    "ci_panel__panel__panel_name": "Second Panel",
                    "ci_panel__panel__panel_version": "2",
                }
            ],
        }

        expected_rel_panels = set([self.panel_1.pk, self.panel_2.pk])

        self.assertEqual(expected_ci_panels, ci_panels)
        self.assertEqual(expected_rel_panels, relevant_panels)
