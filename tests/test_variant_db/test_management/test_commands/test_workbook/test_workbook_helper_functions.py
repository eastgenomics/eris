from django.test import TestCase

from variant_db.management.commands.workbook import (
    _convert_name_to_lowercase,
    _replace_with_underscores,
    _rename_acgs_column,
    _parse_panel,
)


class TestColumnHeaderCleaningFunctions(TestCase):
    """
    Collection of test cases that test each of the workbook column header-cleaning utilities
    """

    def test_convert_name_to_lowercase(self):
        """
        CASE: Test that `_convert_name_to_lowercase` converts names to lowercase, with the exception of
        anything matching the `exclude` argument
        EXPECT: `_convert_name_to_lowercase` converts names to lowercase. `exclude` option skips lowercase
        conversion for matching strings
        """
        self.assertEqual(_convert_name_to_lowercase("PIZZA"), "pizza")
        self.assertEqual(_convert_name_to_lowercase("PizZa"), "pizza")
        # test that PIZZA is ignored when matching `exclude` option is invoked
        self.assertEqual(_convert_name_to_lowercase("PIZZA", "PIZZA"), "PIZZA")
        # test that PIZZA is *not* ignored when non-matching `exclude` option is invoked
        self.assertEqual(
            _convert_name_to_lowercase("PIZZA", "PEPPERONI"), "pizza"
        )
        # tests for the defaults
        self.assertEqual(
            _convert_name_to_lowercase("PIZZA_verdict"), "PIZZA_verdict"
        )
        self.assertEqual(
            _convert_name_to_lowercase("PIZZA_evidence"), "PIZZA_evidence"
        )

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


class TestPanelAssertionHandling(TestCase):
    """
    Test cases that test the panel format assertion (i.e. raising it when needed, avoiding it when not)
    """

    def test_parse_panel_raises_assertion(self):
        """
        CASE: Strings that represent the panel are submitted in various incorrect formats. Expected format
        is `<panel_name>_<optional extra stuff>_<panel_version>`, and the test strings that are submitted to
        `_parse_panel` don't conform to this format.
        EXPECT: `_parse_panel` correctly raises `AssertionError` for all tested cases
        """
        test_strings = [
            # no version
            "HGNC:1100_SG_panel",
            # unexpected characters at end of version
            "CUH_Inherited Stroke_1.0foo",
        ]
        for test_string in test_strings:
            with self.subTest(test_string=test_string), self.assertRaises(
                AssertionError
            ):
                _parse_panel(test_string)

    def test_parse_panel_extracts_panel_name_and_version(self):
        """
        CASE: strings conforming to the format `<panel name>_<optional stuff>_<panel version>` are submitted to
          `_parse_panel`
        EXPECTS: `AssertionError` is not raised, and the resultant `dict` object contains the expected data
        """
        # tuples: (panel string, expected dict result)
        test_data = [
            (
                "CUH_Inherited Stroke_1.0",
                {"name": "CUH_Inherited Stroke", "version": "1.0"},
            ),
            (
                "Hereditary neuropathy or pain disorder - NOT PMP22 copy number_3.0",
                {
                    "name": "Hereditary neuropathy or pain disorder - NOT PMP22 copy number",
                    "version": "3.0",
                },
            ),
            ("Haematuria_2.4", {"name": "Haematuria", "version": "2.4"}),
            (
                "Test_panel_v1.23.45",
                {"name": "Test_panel", "version": "v1.23.45"},
            ),
            (
                "Test_panel_v10.9.31",
                {"name": "Test_panel", "version": "v10.9.31"},
            ),
        ]
        for row in test_data:
            with self.subTest(row=row):
                parsed_panel = _parse_panel(row[0])
                self.assertDictEqual(parsed_panel, row[1])
