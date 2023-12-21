from django.test import TestCase

from requests_app.management.commands.generate import Command
from requests_app.models import (
    Panel,
    SuperPanel,
    ClinicalIndication,
    ClinicalIndicationPanel,
    ClinicalIndicationSuperPanel,
    TestDirectoryRelease,
)


class TestBlockGenepanels_BlankDb(TestCase):
    """
    CASE: Db is fully empty
    EXPECT: Full set of 'empty table' errors
    """

    def test_generate_empty_errors(self):
        cmd = Command()

        expected_errs = (
            "Test Directory has not yet been imported, run: "
            "python manage.py seed td <td.json>"
        )

        with self.assertRaisesRegex(ValueError, expected_errs):
            cmd._block_genepanels_if_db_not_ready()


class TestBlockGenepanels_PendingCiPanels(TestCase):
    def setUp(self) -> None:
        TestDirectoryRelease.objects.create(
            release="8", td_source="xlsx", config_source="json", td_date="2023_04_13"
        )
        self.panel = Panel.objects.create(
            external_id="5",
            panel_source="TD",
            panel_name="My Panel",
            panel_version="5",
            test_directory=True,
            custom=False,
            pending=False,
        )
        self.ci = ClinicalIndication.objects.create(
            r_code="", name="", test_method="ngs", pending=False
        )
        self.cip = ClinicalIndicationPanel.objects.create(
            panel=self.panel, clinical_indication=self.ci, current=True, pending=True
        )

    def test_pending_ci_panel_errors(self):
        """
        CASE: There are CI-Panel entries and TestDirectoryReleases in the db, but
        some CI-Panels are set to pending=True
        EXPECT: Return an error warning the user that pending ci-panels need resolving
        """
        cmd = Command()

        expected_err = (
            "Some ClinicalIndicationPanel table values require manual review. "
            "Please resolve these through the review platform and try again"
        )

        with self.assertRaisesRegex(ValueError, expected_err):
            cmd._block_genepanels_if_db_not_ready()


class TestBlockGenepanels_PendingSuperPanels(TestCase):
    """
    CASE: There are CI-Panel entries and TestDirectoryReleases in the db, but
    some CI-Superpanels are set to pending=True
    EXPECT: Return an error warning the user that pending ci-superpanels need resolving
    """

    def setUp(self) -> None:
        TestDirectoryRelease.objects.create(
            release="8", td_source="xlsx", config_source="json", td_date="2023_04_13"
        )
        self.panel = Panel.objects.create(
            external_id="5",
            panel_source="TD",
            panel_name="My Panel",
            panel_version="5",
            test_directory=True,
            custom=False,
            pending=False,
        )
        self.superpanel = SuperPanel.objects.create(
            external_id="10",
            panel_source="TD",
            panel_name="My SuperPanel",
            panel_version="2",
            test_directory=True,
            custom=False,
            pending=False,
        )
        self.ci = ClinicalIndication.objects.create(
            r_code="", name="", test_method="ngs", pending=False
        )
        self.cip = ClinicalIndicationPanel.objects.create(
            panel=self.panel, clinical_indication=self.ci, current=True, pending=False
        )
        self.cisp = ClinicalIndicationSuperPanel.objects.create(
            superpanel=self.superpanel,
            clinical_indication=self.ci,
            current=True,
            pending=True,
        )

    def test_pending_ci_superpanel_errors(self):
        """
        CASE: There are CI-Panel entries and TestDirectoryReleases in the db, but
        some CI-SuperPanels are set to pending=True
        EXPECT: Return an error warning the user that pending ci-superpanels need resolving
        """
        cmd = Command()
        expected_err = (
            "Some ClinicalIndicationSuperPanel table values require manual review. "
            "Please resolve these through the review platform and try again"
        )

        with self.assertRaisesRegex(ValueError, expected_err):
            cmd._block_genepanels_if_db_not_ready()
