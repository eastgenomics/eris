from django.test import TestCase

from panels_backend.models import (
    Panel,
    ClinicalIndication,
    ClinicalIndicationPanel,
    ClinicalIndicationPanelHistory,
)
from panels_backend.management.commands._queries import (
    activate_clinical_indication_panel,
)


class TestActivateCiPanel_AlreadyExists_Active(TestCase):
    """
    CASE: A CI-Panel already exists and is active
    EXPECT: No change - CI-Panel remains in same state as before function call
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
        EXPECT: No change - CI-Panel remains in same state as before function call
        """
        activate_clinical_indication_panel(self.ci.id, self.panel.id, None)

        # check that the only ci_panel entry is our originally-made one
        cips = ClinicalIndicationPanel.objects.all()
        assert len(cips) == 1
        assert cips[0].current

        # check that no new history data was made
        cip_history = ClinicalIndicationPanelHistory.objects.all()
        assert not len(cip_history)


class TestActivateCiPanel_AlreadyExists_Inactive(TestCase):
    """
    CASE: A CI-Panel already exists BUT it is not active
    EXPECT: CI-Panel becomes activated, and a history entry is made to say this
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
        activate_clinical_indication_panel(self.ci.id, self.panel.id, None)

        # check that the only ci_panel entry is our originally-made one
        with self.subTest():
            cips = ClinicalIndicationPanel.objects.all()
            assert len(cips) == 1
            self.assertEquals(cips[0].id, self.ci_panel.id)

        # check that the ci_panel entry is now active
        with self.subTest():
            assert cips[0].current

        # check that a new history row has been made
        with self.subTest():
            cip_history = ClinicalIndicationPanelHistory.objects.all()
            assert len(cip_history) == 1
            assert cip_history[0].clinical_indication_panel == self.ci_panel
            assert (
                cip_history[0].note
                == "Existing ci-panel link set to active by None"
            )


class TestActivateCiPanel_BrandNew(TestCase):
    """
    CASE: A CI-Panel link hasn't been made before, although the CI and Panel are already in the database.
    EXPECT: CI-Panel is created, activated, and a history entry is made to say this
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

    def test_brand_new(self):
        """
        CASE: A CI-Panel link hasn't been made before, although the CI and Panel are already in the database.
        EXPECT: CI-Panel is created, activated, and a history entry is made to say this
        """
        activate_clinical_indication_panel(self.ci.id, self.panel.id, None)

        # check that the ci_panel are now linked
        with self.subTest():
            self.cips = ClinicalIndicationPanel.objects.all()
            assert len(self.cips) == 1
            self.assertEquals(self.cips[0].panel, self.panel)
            self.assertEquals(self.cips[0].clinical_indication, self.ci)

        # check that the ci_panel entry is now active
        with self.subTest():
            assert self.cips[0].current

        # check that a new history row has been made
        with self.subTest():
            cip_history = ClinicalIndicationPanelHistory.objects.all()
            assert len(cip_history) == 1
            assert cip_history[0].clinical_indication_panel == self.cips[0]
            assert cip_history[0].note == "Created by command line"
