"""
Tested scenario `insert_superpanel_into_db_function`
- core function of inserting SuperPanels, metadata, and links to children
- flag previous and current clinical indication-panel link for review if 
superpanel name or version change in PanelApp API
- nothing changes if superpanel remains the same in PanelApp API


- does not test for superpanel-gene changes - this is dealt with in `insert_gene`
"""

from django.test import TestCase
from django.contrib.auth.models import User

from panels_backend.management.commands.panelapp import SuperPanelClass
from panels_backend.models import (
    Panel,
    SuperPanel,
    PanelSuperPanel,
    ClinicalIndication,
    ClinicalIndicationSuperPanel,
    ClinicalIndicationSuperPanelHistory,
    TestDirectoryRelease,
)
from panels_backend.management.commands.utils import sortable_version
from panels_backend.management.commands._insert_panel import (
    _insert_superpanel_into_db,
)

from .test_insert_gene import len_check_wrapper, value_check_wrapper


class TestInsertNewSuperpanelIntoDb(TestCase):
    def setUp(self) -> None:
        """
        setup conditions for the test
        """
        # child-panels of our SuperPanel, made in advance
        self.child_one = Panel.objects.create(
            external_id="1",
            panel_name="Rhabdo one",
            panel_source="PanelApp",
            panel_version=sortable_version("1.15"),
        )

        self.child_two = Panel.objects.create(
            external_id="2",
            panel_name="Rhabdo_two",
            panel_source="PanelApp",
            panel_version=sortable_version("1.16"),
        )

        self.first_clinical_indication = ClinicalIndication.objects.create(
            r_code="R123",
            name="Test clinical indication",
            test_method="Test method",
        )

        self.user = User.objects.create_user(username="test", is_staff=True)

    def test_that_a_new_superpanel_is_made(
        self,
    ):
        """
        Test that the a brand new superpanel is inserted into the db,
        and links formed with its child panels.
        """
        errors = []

        superpanel = SuperPanelClass(
            id="1142",
            name="Acute rhabdomyolyosis",
            version="1.15",
            panel_source="PanelApp",
            genes=[],
            regions=[],
            child_panels=[],
        )

        child_panels = [self.child_one, self.child_two]

        _insert_superpanel_into_db(superpanel, child_panels, self.user)

        # look at db changes
        superpanel = SuperPanel.objects.all()
        ci_superpanel = ClinicalIndicationSuperPanel.objects.all()
        panel_superpanel = PanelSuperPanel.objects.all()

        # a superpanel should be made and set to pending
        errors += len_check_wrapper(superpanel, "superpanel", 1)
        errors += value_check_wrapper(
            superpanel[0].external_id, "ext id", "1142"
        )
        errors += value_check_wrapper(superpanel[0].pending, "pending", False)

        # there won't be a CI link because this is a brand new superpanel
        errors += len_check_wrapper(
            ci_superpanel, "clinical indication-superpanel", 0
        )

        # there should be links to child panels
        errors += len_check_wrapper(
            panel_superpanel, "panel-superpanel links", 2
        )
        errors += value_check_wrapper(
            panel_superpanel[0].panel, "panel-superpanel Panel", self.child_one
        )
        errors += value_check_wrapper(
            panel_superpanel[1].panel, "panel-superpanel Panel", self.child_two
        )

        assert not errors, errors


class TestInsertSuperpanelVersionChange(TestCase):
    """
    Testing case when a superpanel has a version update
    It should inherit the CI of the previous version,
    and be set to Pending
    """

    def setUp(self) -> None:
        """
        setup conditions for the test
        """
        # child-panels of our SuperPanel, made in advance
        self.child_one = Panel.objects.create(
            external_id="1",
            panel_name="Rhabdo one",
            panel_source="PanelApp",
            panel_version=sortable_version("1.15"),
        )

        self.child_two = Panel.objects.create(
            external_id="2",
            panel_name="Rhabdo_two",
            panel_source="PanelApp",
            panel_version=sortable_version("1.16"),
        )
        self.child_two.save()

        self.first_clinical_indication = ClinicalIndication.objects.create(
            r_code="R123",
            name="Test clinical indication",
            test_method="Test method",
        )

        self.old_superpanel = SuperPanel.objects.create(
            external_id="1142",
            panel_name="Acute rhabdomyolyosis",
            panel_source="PanelApp",
            panel_version=sortable_version("1.16"),
        )

        self.ci = ClinicalIndication.objects.create(
            r_code="Rtest", name="test_CI", test_method="NGS"
        )

        self.td_version = TestDirectoryRelease.objects.create(release="5")

        self.ci_old_superpanel_link = (
            ClinicalIndicationSuperPanel.objects.create(
                superpanel=self.old_superpanel,
                clinical_indication=self.ci,
                current=True,
            )
        )

        self.child_panels = [self.child_one, self.child_two]

    def test_old_ci_superpanel_link_flagged_on_superpanel_version_change(
        self,
    ):
        """
        example scenario (superpanel version upgrade):
        - first superpanel is already in the database
        - in our test, we link it to a CI
        - second superpanel comes in with the same external-id, but different version
        - we expect the first superpanel-ci link to be flagged as pending
        - and we expect a new, flagged link between second panel and first clinical indication
        """
        errors = []

        new_superpanel = SuperPanelClass(
            id="1142",
            name="Acute rhabdomyolyosis",
            version="1.20",  # higher version
            panel_source="PanelApp",
            genes=[],
            regions=[],
            child_panels=[],
        )

        _insert_superpanel_into_db(new_superpanel, self.child_panels, user=None)

        # check what's in the db now
        ci_superpanels = ClinicalIndicationSuperPanel.objects.all()
        superpanels = SuperPanel.objects.all()
        ci_superpanels_history = ClinicalIndicationSuperPanelHistory.objects.all()

        errors += len_check_wrapper(
            ci_superpanels, "clinical indication-panel", 2
        )
        errors += len_check_wrapper(superpanels, "superpanels", 2)
        errors += len_check_wrapper(
            ci_superpanels_history, "ci-superpanel history", 2
        )
        
        errors += value_check_wrapper(ci_superpanels_history[0].user, "history user", None)

        errors += value_check_wrapper(
            superpanels[1].panel_version,
            "second panel version",
            sortable_version("1.20"),
        )  # assert that the second panel version is the newer one

        # Both CI-SuperPanel links should now be pending=True,
        # awaiting review
        errors += value_check_wrapper(
            ci_superpanels[0].superpanel,
            "Superpanel in first link",
            self.old_superpanel,
        )  # just to ascertain that the old superpanel is first in QuerySet
        errors += value_check_wrapper(
            ci_superpanels[0].pending, "first CI-superpanel pending", True
        )
        errors += value_check_wrapper(
            ci_superpanels[0].current, "first CI-superpanel current", False
        )

        errors += value_check_wrapper(
            ci_superpanels[1].pending,
            "second clinical indication-superpanel pending",
            True,
        )
        errors += value_check_wrapper(
            ci_superpanels[1].current, "second CI-superpanel current", True
        )

        assert not errors, errors


class TestInsertSuperpanelNameChange(TestCase):
    """
    Testing case when a superpanel has a name update
    It should inherit the CI of the previous version,
    and be set to Pending
    """

    def setUp(self) -> None:
        """
        setup conditions for the test
        """
        # child-panels of our SuperPanel, made in advance
        self.child_one = Panel.objects.create(
            external_id="1",
            panel_name="Rhabdo one",
            panel_source="PanelApp",
            panel_version=sortable_version("1.15"),
        )

        self.child_two = Panel.objects.create(
            external_id="2",
            panel_name="Rhabdo_two",
            panel_source="PanelApp",
            panel_version=sortable_version("1.16"),
        )
        self.child_two.save()

        self.first_clinical_indication = ClinicalIndication.objects.create(
            r_code="R123",
            name="Test clinical indication",
            test_method="Test method",
        )

        self.old_superpanel = SuperPanel.objects.create(
            external_id="1142",
            panel_name="Acute rhabdomyolyosis",
            panel_source="PanelApp",
            panel_version=sortable_version("1.16"),
        )

        self.ci = ClinicalIndication.objects.create(
            r_code="Rtest", name="test_CI", test_method="NGS"
        )

        self.td_version = TestDirectoryRelease.objects.create(release="5")

        self.ci_old_superpanel_link = (
            ClinicalIndicationSuperPanel.objects.create(
                superpanel=self.old_superpanel,
                clinical_indication=self.ci,
                current=True,
            )
        )

        self.child_panels = [self.child_one, self.child_two]

    def test_previous_ci_superpanel_flagged_on_superpanel_name_change(
        self,
    ):
        """
        example scenario (superpanel version upgrade):
        - first superpanel and first clinical indication are already linked in the database
        - second panel comes in with the same external-id, but different panel name
        EXPECT:
        - first superpanel and CI have their link flagged for review
        - a new link is made between second superpanel and first clinical indication for review
        """
        errors = []

        superpanel_input = SuperPanelClass(
            id="1142",
            name="Acute rhabdomyolosis with a different name",  # note the different name
            version="1.16",
            panel_source="PanelApp",
            genes=[],
            regions=[],
        )

        _insert_superpanel_into_db(superpanel_input, self.child_panels, None)

        ci_superpanels = ClinicalIndicationSuperPanel.objects.all()
        superpanels = SuperPanel.objects.all()

        errors += len_check_wrapper(
            ci_superpanels, "ClinicalIndicationSuperpanel", 2
        )  # assert that there is a new clinical indication-panel

        errors += value_check_wrapper(
            ci_superpanels[0].pending,
            "first clinical indication-panel pending",
            True,
        )  # assert that the first clinical indication-panel is flagged for review
        errors += value_check_wrapper(
            ci_superpanels[1].pending,
            "second clinical indication-panel pending",
            True,
        )  # assert that the second clinical indication-panel is flagged for review

        errors += value_check_wrapper(
            superpanels[1].panel_name,
            "second panel name",
            "Acute rhabdomyolosis with a different name",
        )  # assert second panel name is "Acute rhabdomyolosis with a different name"

        assert not errors, errors


class TestInsertSuperpanelUnchanged(TestCase):
    """
    Testing case when a superpanel hasn't changed in PanelApp
    since the last Eris update.
    EXPECT: SuperPanel not added to the db.
    """

    def setUp(self) -> None:
        """
        setup conditions for the test
        """
        # child-panels of our SuperPanel, made in advance
        self.child_one = Panel.objects.create(
            external_id="1",
            panel_name="Rhabdo one",
            panel_source="PanelApp",
            panel_version=sortable_version("1.15"),
        )

        self.child_two = Panel.objects.create(
            external_id="2",
            panel_name="Rhabdo_two",
            panel_source="PanelApp",
            panel_version=sortable_version("1.16"),
        )

        self.first_clinical_indication = ClinicalIndication.objects.create(
            r_code="R123",
            name="Test clinical indication",
            test_method="Test method",
        )

        self.old_superpanel = SuperPanel.objects.create(
            external_id="1142",
            panel_name="Acute rhabdomyolyosis",
            panel_source="PanelApp",
            panel_version=sortable_version("1.16"),
        )

        self.ci = ClinicalIndication.objects.create(
            r_code="Rtest", name="test_CI", test_method="NGS"
        )

        self.td_version = TestDirectoryRelease.objects.create(release="5")

        self.ci_old_superpanel_link = (
            ClinicalIndicationSuperPanel.objects.create(
                superpanel=self.old_superpanel,
                clinical_indication=self.ci,
                current=True,
            )
        )

        self.child_panels = [self.child_one, self.child_two]

    def test_panel_unchanged_in_panelapp_api(
        self,
    ):
        """
        SCENARIO: superpanel unchanged between uploads in PanelApp API
        EXPECT: no changes in the database
        """
        errors = []

        superpanel_input = SuperPanelClass(
            id="1142",
            name="Acute rhabdomyolyosis",
            version=sortable_version("1.16"),
            panel_source="PanelApp",
            genes=[],
            regions=[]
            # child_panels=[child_one, child_two]
        )

        _insert_superpanel_into_db(
            superpanel_input, self.child_panels, "PanelApp"
        )

        superpanels = SuperPanel.objects.all()
        history = ClinicalIndicationSuperPanelHistory.objects.all()

        errors += len_check_wrapper(
            superpanels, "superpanel", 1
        )  # assert only one SuperPanel objects

        errors += len_check_wrapper(
            history, "history", 0
        )  # didn't make a history/link with CI

        errors += value_check_wrapper(
            superpanels[0].panel_name,
            "superpanel name",
            "Acute rhabdomyolyosis",
        )  # assert nothing has changed to the existing panel

        self.assertEqual(self.old_superpanel, superpanels[0])

        assert not errors, errors
