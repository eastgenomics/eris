from django.test import TestCase
from variant_db.management.commands.insert import _rename_key, _subset_row

class TestInsertHelperFunctions(TestCase):
    def test_rename_key(self):
        test_dict = {"first_key": 1, "second_key": 2}
        test_output = _rename_key(test_dict, "first_key", "renamed_first_key")
        self.assertDictEqual(test_output, {"renamed_first_key": 1, "second_key": 2})
    
    def test_subset_row(self):
        test_dict = {"first_key": 1, "second_key": 2, "third_key": 3, "fourth_key": 4}
        test_output_1 = _subset_row(test_dict, *["first_key", "third_key"])
        self.assertDictEqual(test_output_1, {"first_key": 1, "third_key": 3})
        test_output_2 = _subset_row(test_dict, "second_key", "fourth_key")
        self.assertDictEqual(test_output_2, {"second_key": 2, "fourth_key": 4})