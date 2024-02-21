from django.test import TestCase

from panels_backend.models import (
    Panel,
    ClinicalIndication,
    ClinicalIndicationPanel,
    ClinicalIndicationPanelHistory,
)
from panels_backend.management.commands._queries import (
    deactivate_clinical_indication_panel,
)


class TestDeactivateCiPanel_AlreadyExists_Active(TestCase):
    """
    CASE: A CI-Panel already exists and is active
    EXPECT: CI-Panel entry is changed to current=False
    """

    def setUp(self) -> None:
        self.panel = Panel.objects.create(
            external_id="105",
            panel_name="A nice test panel",
            panel_source="PanelApp",
            panel_version="3",
        )

        self.ci = ClinicalIndication.objects.create(
            r_code="R1", name="Our CI", test_method="small panel"
        )

        self.ci_panel = ClinicalIndicationPanel.objects.create(
            panel=self.panel, clinical_indication=self.ci, current=True
        )

    def test_already_exists_active(self):
        """
        CASE: A CI-Panel already exists and is active
        EXPECT: CI-Panel entry is changed to current=False
        """
        deactivate_clinical_indication_panel(self.ci.id, self.panel.id, None)

        # check that the only ci_panel entry is our originally-made one
        cips = ClinicalIndicationPanel.objects.all()
        assert len(cips) == 1
        self.assertEquals(cips[0], self.ci_panel)

        # check that the ci_panel entry is now NOT current
        with self.subTest():
            assert not cips[0].current

        # check that a new history row was made
        with self.subTest():
            cip_history = ClinicalIndicationPanelHistory.objects.all()
            assert len(cip_history) == 1
            assert cip_history[0].clinical_indication_panel == self.ci_panel
            assert (
                cip_history[0].note
                == "Existing ci-panel link set to inactive by None"
            )


class TestDectivateCiPanel_AlreadyExists_Inactive(TestCase):
    """
    CASE: A CI-Panel already exists AND IS ALREADY inactive
    EXPECT: CI-Panel remains unchanged, with no history log
    """

    def setUp(self) -> None:
        self.panel = Panel.objects.create(
            external_id="105",
            panel_name="A nice test panel",
            panel_source="PanelApp",
            panel_version="3",
        )

        self.ci = ClinicalIndication.objects.create(
            r_code="R1", name="Our CI", test_method="small panel"
        )

        self.ci_panel = ClinicalIndicationPanel.objects.create(
            panel=self.panel,
            clinical_indication=self.ci,
            current=False,  # N.B. not active
        )

    def test_already_exists_inactive(self):
        """
        CASE: A CI-Panel already exists BUT it is not active
        EXPECT: CI-Panel becomes activated, and a history entry is made to say this
        """
        deactivate_clinical_indication_panel(self.ci.id, self.panel.id, None)

        # check that the only ci_panel entry is our originally-made one
        with self.subTest():
            cips = ClinicalIndicationPanel.objects.all()
            assert len(cips) == 1
            self.assertEquals(cips[0].id, self.ci_panel.id)

        # check that the ci_panel entry is still active
        with self.subTest():
            assert not cips[0].current

        # check that a no new history row has been made
        with self.subTest():
            cip_history = ClinicalIndicationPanelHistory.objects.all()
            assert not cip_history


class TestDeactivateCiPanel_NoExistingLink(TestCase):
    """
    CASE: A CI-Panel link hasn't been made before, although the CI and Panel are already in the database.
    EXPECT: Nothing happens - no new link is made, no history is logged
    """

    def setUp(self) -> None:
        self.panel = Panel.objects.create(
            external_id="105",
            panel_name="A nice test panel",
            panel_source="PanelApp",
            panel_version="3",
        )

        self.ci = ClinicalIndication.objects.create(
            r_code="R1", name="Our CI", test_method="small panel"
        )

    def test_no_existing_link(self):
        """
        CASE: A CI-Panel link hasn't been made before, although the CI and Panel are already in the database.
        EXPECT: Nothing happens - no new link is made, no history is logged
        """
        deactivate_clinical_indication_panel(self.ci.id, self.panel.id, None)

        # check that no link is made between CI and panel
        with self.subTest():
            self.cips = ClinicalIndicationPanel.objects.all()
            assert not self.cips

        # check that no history row has been made
        with self.subTest():
            cip_history = ClinicalIndicationPanelHistory.objects.all()
            assert not cip_history
