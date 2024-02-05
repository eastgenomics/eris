import pandas as pd
from io import StringIO
from django.test import TestCase
from variant_db.management.commands.insert import ACGS_COLUMNS

from variant_db.management.commands.workbook import *


class TestColumnHeaderCleaningFunctions(TestCase):
    @classmethod
    def setUpTestData(cls):
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

        cls.input = StringIO(csv_string)

    def test_read(self):
        df = read_workbook(self.input)
        print(df)
