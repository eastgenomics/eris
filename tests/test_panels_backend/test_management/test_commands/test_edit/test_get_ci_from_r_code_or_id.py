from django.test import TestCase

from panels_backend.models import (
    ClinicalIndication,
)
from panels_backend.management.commands.edit import get_ci_from_r_code_or_id


class TestGetCi_Rcode(TestCase):
    """
    Cases where:
    - a user requests a CI by its valid R code
    - a user requests a CI that has multiple database entries under an R code
    - a user requests a CI that doesn't exist in the database
    """

    def setUp(self) -> None:
        self.ci_single_entry = ClinicalIndication.objects.create(
            r_code="R123.4", name="Some CI", test_method="large panel"
        )

        self.ci_double_entry_1 = ClinicalIndication.objects.create(
            r_code="R693.1", name="Duplicate One", test_method="large panel"
        )

        self.ci_double_entry_2 = ClinicalIndication.objects.create(
            r_code="R693.1", name="Duplicate Two", test_method="large panel"
        )

    def test_get_ci_r_code_valid(self):
        """
        CASE: Only CI R code is provided. It's valid
        EXPECT: A single ClinicalIndication result is returned that matches
        the user-provided R code
        """
        user_r_code = "R123.4"
        user_ci_id = None
        result = get_ci_from_r_code_or_id(user_r_code, user_ci_id)
        self.assertEqual(self.ci_single_entry, result)

    def test_get_ci_r_code_two_entries(self):
        """
        CASE: Only CI R code is provided. It matches 2 results in the db
        EXPECT: An error is thrown telling the user to use ID instead
        """
        user_r_code = "R693.1"
        user_ci_id = None
        with self.assertRaisesRegex(
            AssertionError,
            "More than one "
            "clinical indication identified with "
            f"r-code {user_r_code}. Use clinical "
            "indication database id instead to be "
            "more specific.",
        ):
            get_ci_from_r_code_or_id(user_r_code, user_ci_id)

    def test_get_ci_r_code_invalid_entries(self):
        """
        CASE: Only CI R code is provided. It matches no results in the db
        EXPECT: An error is thrown telling the user the CI wasn't found
        """
        user_r_code = "R10.1"
        user_ci_id = None
        with self.assertRaisesRegex(
            IndexError, "No clinical indication found"
        ):
            get_ci_from_r_code_or_id(user_r_code, user_ci_id)


class TestGetCi_Id(TestCase):
    """
    Cases where:
    - a user requests a CI by its valid ID
    - a user requests a CI by an ID which doesn't exist
    """

    def setUp(self) -> None:
        self.ci_single_entry = ClinicalIndication.objects.create(
            r_code="R123.4", name="Some CI", test_method="large panel"
        )

    def test_get_ci_id_valid(self):
        """
        CASE: Only CI ID is provided. It's valid
        EXPECT: A single ClinicalIndication result is returned that matches
        the user-provided ID
        """
        user_r_code = None
        user_ci_id = self.ci_single_entry.id
        result = get_ci_from_r_code_or_id(user_r_code, user_ci_id)
        self.assertEqual(self.ci_single_entry, result)

    def test_get_ci_id_invalid(self):
        """
        CASE: Only CI ID is provided. It matches no results in the db
        EXPECT: An error is thrown telling the user the CI wasn't found
        """
        user_r_code = None
        user_ci_id = "5"
        with self.assertRaisesRegex(
            ClinicalIndication.DoesNotExist,
            "The clinical indication ID 5 was not found in the database",
        ):
            get_ci_from_r_code_or_id(user_r_code, user_ci_id)
