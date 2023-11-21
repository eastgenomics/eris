from django.test import TestCase

from requests_app.management.commands._insert_ci import _check_td_version_valid


class TestCheckTdValid_ValidCases(TestCase):
    """
    Ensure that the test directory version validity checker, passes
    when the currently-uploaded version of the td is higher than the
    most-recent version in the database.
    """

    def test_valid_case_one(self):
        """
        CASE: Straightforward case where versions use the same syntax
        EXPECT: pass
        """
        td_upload = "1.0.1"
        latest_in_db = "1.0.0"
        _check_td_version_valid(td_upload, latest_in_db, False)

    def test_valid_case_two(self):
        """
        CASE: Straightforward case where versions use different syntax
        EXPECT: pass
        """
        td_upload = "1.0.1"
        latest_in_db = "1"
        _check_td_version_valid(td_upload, latest_in_db, False)

    def test_valid_case_nothing_in_db(self):
        """
        CASE: The db doesn't contain a version - it might be brand new
        EXPECT: pass
        """
        td_upload = "1.0.1"
        latest_in_db = None
        _check_td_version_valid(td_upload, latest_in_db, False)

    def test_valid_case_force(self):
        """
        CASE: The db version is older but the user passes force
        EXPECT: pass
        """
        td_upload = "1.0.1"
        latest_in_db = "2.0"
        _check_td_version_valid(td_upload, latest_in_db, True)


class TestCheckTdValid_FailingCases(TestCase):
    """
    Ensure that the test directory version validity checker, FAILS
    when the currently-uploaded version of the td is lower than or equal to
    the most-recent version in the database.
    """

    def test_invalid_case_one(self):
        """
        CASE: Straightforward case where versions match each other, but use different syntax
        which is synonymous
        EXPECT: Exception is raised
        """
        td_upload = "1.0.0"
        latest_in_db = "1"

        expected_err = f"TD version {td_upload} is less than or the same as"
        f" the version currently in the db, {latest_in_db}."
        f" Abandoning import."

        with self.assertRaisesRegex(Exception, expected_err):
            _check_td_version_valid(td_upload, latest_in_db, False)

    def test_invalid_case_two(self):
        """
        CASE: Straightforward, same-version-syntax, with a newer version already in the db
        EXPECT: Exception is raised
        """
        td_upload = "1.0.0"
        latest_in_db = "1.0.1"

        expected_err = f"TD version {td_upload} is less than or the same as"
        f" the version currently in the db, {latest_in_db}."
        f" Abandoning import."

        with self.assertRaisesRegex(Exception, expected_err):
            _check_td_version_valid(td_upload, latest_in_db, False)

    def test_invalid_case_three(self):
        """
        CASE: Less straightforward, with a newer version already in the db
        EXPECT: Exception is raised
        """
        td_upload = "1.0.0"
        latest_in_db = "2"

        expected_err = f"TD version {td_upload} is less than or the same as"
        f" the version currently in the db, {latest_in_db}."
        f" Abandoning import."

        with self.assertRaisesRegex(Exception, expected_err):
            _check_td_version_valid(td_upload, latest_in_db, False)
