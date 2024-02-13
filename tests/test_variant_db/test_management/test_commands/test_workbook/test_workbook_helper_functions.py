from django.test import TestCase

from variant_db.management.commands.workbook import (
    _convert_name_to_lowercase,
    _replace_with_underscores,
    _rename_acgs_column,
)


class TestColumnHeaderCleaningFunctions(TestCase):
    """
    Collection of test cases that test each of the workbook column header-cleaning utilities

    CASE: Test that `_convert_name_to_lowercase` converts names to lowercase, with the exception of
    anything matching the `exclude` argument
    EXPECT: `_convert_name_to_lowercase` converts names to lowercase. `exclude` option skips lowercase
    conversion for matching strings
    """

    def test_convert_name_to_lowercase(self):
        self.assertEqual(_convert_name_to_lowercase("PIZZA"), "pizza")
        self.assertEqual(_convert_name_to_lowercase("PizZa"), "pizza")
        # test that PIZZA is ignored when matching `exclude` option is invoked
        self.assertEqual(_convert_name_to_lowercase("PIZZA", "PIZZA"), "PIZZA")
        # test that PIZZA is *not* ignored when non-matching `exclude` option is invoked
        self.assertEqual(_convert_name_to_lowercase("PIZZA", "PEPPERONI"), "pizza")
        # tests for the defaults
        self.assertEqual(_convert_name_to_lowercase("PIZZA_verdict"), "PIZZA_verdict")
        self.assertEqual(_convert_name_to_lowercase("PIZZA_evidence"), "PIZZA_evidence")

    def test_replace_with_underscores(self):
        """
        Tests that `_replace_with_underscores` behaves as expected.

        CASE: Test that `_replace_with_underscores` replaces whitespace with underscores,
        except in the cases where "ID" is found where an underscore should be placed between
        "ID" and the previous token
        EXPECT: `_replace_with_underscores` does what's outlined in the CASE.
        """
        self.assertEqual(
            _replace_with_underscores("margherita pizza"), "margherita_pizza"
        )
        self.assertEqual(
            _replace_with_underscores("margherita_pizza"), "margherita_pizza"
        )
        self.assertEqual(_replace_with_underscores("pizzaID"), "pizza_ID")
        self.assertEqual(_replace_with_underscores("$%*ID"), "$%*ID")

    def test_rename_acgs_column(self):
        """
        Tests that `_rename_ACGS_column` behaves as expected.

        CASE: Test that `_rename_acgs_column` appends "_verdict" to the string if "_evidence" not
        already appended, and ignores non-ACGS columns
        EXPECT: `_rename_acgs_column` does what's outlined in the CASE.
        """
        # cases where _verdict should be added to the string
        self.assertEqual(_rename_acgs_column("PS1"), "PS1_verdict")
        self.assertEqual(_rename_acgs_column("PVS1"), "PVS1_verdict")
        self.assertEqual(_rename_acgs_column("BP1"), "BP1_verdict")
        self.assertEqual(_rename_acgs_column("BM6"), "BM6_verdict")
        self.assertEqual(_rename_acgs_column("BA1"), "BA1_verdict")
        self.assertEqual(_rename_acgs_column("PP3"), "PP3_verdict")
        # cases that shouldn't get _verdict added to the string
        self.assertEqual(_rename_acgs_column("PS1_evidence"), "PS1_evidence")
        self.assertEqual(_rename_acgs_column("PIZZA"), "PIZZA")
