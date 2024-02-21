from django.test import TestCase

from panels_backend.models import (
    Panel,
)
from panels_backend.management.commands.edit import get_panel_from_id_or_name


class TestGetPanel_Id(TestCase):
    """
    Cases where:
    - a user requests a panel by its valid ID
    - a user requests a panel by an ID which doesn't exist
    """

    def setUp(self) -> None:
        self.panel_single_entry = Panel.objects.create(
            external_id="200",
            panel_name="A lovely panel",
            panel_source="PanelApp",
            panel_version="5",
        )

    def test_get_panel_id_valid(self):
        """
        CASE: Only panel ID is provided. It's valid
        EXPECT: A single Panel result is returned that matches
        the user-provided ID
        """
        user_panel_id = self.panel_single_entry.id
        user_panel_name = None
        result = get_panel_from_id_or_name(user_panel_id, user_panel_name)
        self.assertEqual(self.panel_single_entry, result)

    def test_get_panel_id_invalid(self):
        """
        CASE: Only Panel ID is provided. It matches no results in the db
        EXPECT: An error is thrown telling the user the Panel wasn't found
        """
        user_panel_id = "100"
        user_panel_name = None

        error_msg = (
            f"The panel ID {user_panel_id} was not found in the database"
        )
        with self.assertRaisesRegex(Panel.DoesNotExist, error_msg):
            get_panel_from_id_or_name(user_panel_id, user_panel_name)


class TestGetPanel_Name(TestCase):
    """
    Cases where:
    - a user requests a panel by its valid name
    - a user requests a panel by its valid name BUT it is ambiguous
    - a user requests a panel by a name which doesn't exist
    """

    def setUp(self) -> None:
        self.panel_single_entry = Panel.objects.create(
            external_id="200",
            panel_name="A lovely panel",
            panel_source="PanelApp",
            panel_version="5",
        )

        self.panel_two_entries_1 = Panel.objects.create(
            external_id="400",
            panel_name="A different lovely panel",
            panel_source="PanelApp",
            panel_version="5",
        )

        self.panel_two_entries_2 = Panel.objects.create(
            external_id="401",
            panel_name="A different lovely panel",
            panel_source="PanelApp",
            panel_version="4",
        )

    def test_get_panel_name_valid(self):
        """
        CASE: Only panel name is provided. It's valid and there's 1 match only
        EXPECT: A single Panel result is returned that matches
        the user-provided name
        """
        user_panel_id = None
        user_panel_name = self.panel_single_entry.panel_name
        result = get_panel_from_id_or_name(user_panel_id, user_panel_name)
        self.assertEqual(self.panel_single_entry, result)

    def test_get_panel_name_invalid(self):
        """
        CASE: Only Panel name is provided. It matches no results in the db
        EXPECT: An error is thrown telling the user the Panel wasn't found
        """
        user_panel_id = None
        user_panel_name = "doesn't_exist"

        error_msg = f"No panel found"
        with self.assertRaisesRegex(IndexError, error_msg):
            get_panel_from_id_or_name(user_panel_id, user_panel_name)

    def test_get_panel_name_two_entries(self):
        """
        CASE: Only Panel name is provided. It matches 2 results in the db
        EXPECT: An error is thrown telling the user to use ID instead
        """
        user_panel_id = None
        user_panel_name = "A different lovely panel"

        error_msg = f"More than one {user_panel_name} identified."
        "Use python manage.py edit [--cid/--rcode] <ci> pid <panel-id> "
        "<add/remove> instead."

        with self.assertRaisesRegex(AssertionError, error_msg):
            get_panel_from_id_or_name(user_panel_id, user_panel_name)
