import re
import pandas as pd
from io import StringIO
from django.test import TestCase
from variant_db.management.commands.insert import ACGS_COLUMNS

import variant_db.management.commands.workbook as workbook


class TestReadWorkbook(TestCase):
    """
    Collection of test cases for the workbook reading and parsing utilities
    """

    @classmethod
    def setUpTestData(cls):
        """
        The test data defined here "mocks" a workbook CSV as a single row.
        It is first generated as a string (header, newline, values), and
        then passed into the read_workbook function as a `StringIO` instance,
        which replicates the action of passing a CSV file into the CLI
        """
        numeric_headers = [
            "POS",
            "instrumentID",
            "specimenID",
            "batchID",
            "test code",
            "probesetID",
        ]
        numeric_values = ["1" for x in numeric_headers]

        string_headers = [
            "HGSVc",
            "Consequence",
            "Comment",
            "CI",
            "ref_genome",
            "Organisation",
            "Institution",
            "Associated disease",
            "Known inheritance",
            "Prevalence",
            "category",
            "assertion_criteria",
            "allele_origin",
            "assay_method",
            "collection_method",
            "affected_status",
        ] + [x.replace("_verdict", "") for x in ACGS_COLUMNS]
        string_values = ["pizza" for x in string_headers]

        misc_headers = ["CHROM", "REF", "ALT", "date", "interpreted", "panel"]
        misc_values = [
            "1",
            "A",
            "C",
            "01/01/2024",
            "Yes",
            "basil_1.0;oregano_1.0;tomato_1.0",
        ]

        csv_string = "{0}\n{1}".format(
            ",".join(numeric_headers + string_headers + misc_headers),
            ",".join(numeric_values + string_values + misc_values),
        )

        wb_records = workbook.read_workbook(StringIO(csv_string))
        cls.wb_records = wb_records
        cls.wb_row = wb_records[0]

    def test_read(self):
        """
        Tests that `read_workbook` returns a list of dicts

        CASE: `wb_records` tested for `list` identity; `wb_row` tested for `dict` identity
        EXPECT: `wb_records` and `wb_row` are `list` and `dict` types respectively
        """
        self.assertIsInstance(self.wb_records, list)
        self.assertIsInstance(self.wb_row, dict)

    def test_acgs_columns(self):
        """
        Test that all ACGS columns are returned by `read_workbook`

        CASE: Exhaustive list of ACGS column members insersected with workbook header
        EXPECT: All members of ACGS columns are present in workbook header names
        """
        row_acgs_columns = [x for x in self.wb_row.keys() if x in ACGS_COLUMNS]
        self.assertListEqual(row_acgs_columns, ACGS_COLUMNS)

    def test_headers_are_lowercase(self):
        """
        Test that non-ACGS column headers are lowercase

        CASE: non-ACGS columns tested for lowercase identity
        EXPECT: All non-ACGS columns are lowercase
        """
        non_acgs_column_names = [x for x in self.wb_row.keys() if x not in ACGS_COLUMNS]
        are_lowercase = [x.islower() for x in non_acgs_column_names]
        self.assertTrue(all(are_lowercase))

    def test_headers_have_no_whitespace(self):
        """
        Test that whitespace is cleaned correctly

        CASE: columns are tested for present of whitespace
        EXPECT: No whitespace found in any columns
        """
        non_acgs_column_names = [x for x in self.wb_row.keys() if x not in ACGS_COLUMNS]
        have_no_whitespace = [x.rfind(" ") == -1 for x in non_acgs_column_names]
        self.assertTrue(all(have_no_whitespace))

    def test_wb_row(self):
        """
        Tests that a column of data is handled correctly

        CASE: An arbitrary field exists and has the expected data ("chrom" <- 1)
        EXPECT: "chrom" exists and has value int(1)
        """
        self.assertEqual(self.wb_row["chrom"], 1)

    def test_wb_row_panels(self):
        """
        Tests that the panel parsing functions correctly split the
        ";"-separated panel entry into a list.

        CASE: `wb_panels` tested for length, and contents tested for `dict` membership
        EXPECT: `wb_panels` is a list with 3 entries. Two arbitrary entries are `dicts` 
        with "name" <- (expected string) and "version" <- "1.0"
        consist of dicts, with pairs of tags for panel name and version
        """
        wb_panels = self.wb_row["panels"]
        panel_a = wb_panels[0]
        panel_c = wb_panels[-1]
        self.assertEqual(len(wb_panels), 3)
        self.assertDictEqual(panel_a, {"name": "basil", "version": "1.0"})
        self.assertDictEqual(panel_c, {"name": "tomato", "version": "1.0"})
