from django.test import TestCase

from requests_app.management.commands.generate import Command


class TestBlockGenepanels_BlankDb(TestCase):
    """
    CASE: Db is fully empty
    EXPECT: Full set of 'empty table' errors
    """

    def test_generate_empty_errors(self):
        cmd = Command()
        actual_errs = cmd._block_genepanels_if_db_not_ready()
        expected_errs = (
            "ClinicalIndicationPanel table is empty, run: python manage.py "
            "seed td <td.json>; Test Directory has not yet been imported, run: "
            "python manage.py seed td <td.json>"
        )
        self.assertEqual(expected_errs, actual_errs)


class TestBlockGenepanels_PendingPanels(TestCase):
    """
    CASE: There are CI-Panel entries and TestDirectoryReleases in the db, but
    some panels are set to pending=True
    EXPECT: Return an error warning the user that pending panels need resolving
    """

    # TODO: write test case


class TestBlockGenepanels_PendingSuperPanels(TestCase):
    """
    CASE: There are CI-Panel entries and TestDirectoryReleases in the db, but
    some panels are set to pending=True
    EXPECT: Return an error warning the user that pending panels need resolving
    """

    # TODO: write test case
