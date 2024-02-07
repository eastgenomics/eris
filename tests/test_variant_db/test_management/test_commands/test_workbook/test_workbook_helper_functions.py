from django.test import TestCase

from variant_db.management.commands.workbook import _convert_name_to_lowercase, _replace_with_underscores, _rename_acgs_column

class TestColumnHeaderCleaningFunctions(TestCase):
    """
    Collection of test cases that test each of the workbook column header-cleaning utilities
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
        self.assertEqual(_replace_with_underscores("margherita pizza"), "margherita_pizza")
        self.assertEqual(_replace_with_underscores("margherita_pizza"), "margherita_pizza")
        self.assertEqual(_replace_with_underscores("pizzaID"), "pizza_ID")
    
    def test_rename_acgs_column(self):
        self.assertEqual(_rename_acgs_column("PS1"), "PS1_verdict")
        self.assertEqual(_rename_acgs_column("PS1_evidence"), "PS1_evidence")
        self.assertEqual(_rename_acgs_column("PIZZA"), "PIZZA")