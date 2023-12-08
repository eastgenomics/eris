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
                    "ci_panel__panel__external_id": "109",
                    "ci_panel__panel__panel_name": "First Panel",
                    "ci_panel__panel__panel_version": "5",
                }
            ],
            "R2": [
                {
                    "ci_panel__clinical_indication__r_code": "R2",
                    "ci_panel__clinical_indication_id__name": "Condition 2",
                    "ci_panel__panel__external_id": "209",
                    "ci_panel__panel__panel_name": "Second Panel",
                    "ci_panel__panel__panel_version": "2",
                }
            ],
        }

        expected_rel_panels = set(["109", "209"])

        self.assertEqual(ci_panels, expected_ci_panels)
        self.assertEqual(relevant_panels, expected_rel_panels)
