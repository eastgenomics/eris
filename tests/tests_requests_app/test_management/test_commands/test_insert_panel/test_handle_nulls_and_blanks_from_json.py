from django.test import TestCase

from requests_app.management.commands._insert_panel import _handle_nulls_and_blanks_from_json


class TestHandleNullsAndBlanks_CasesEquivalentToNoneData(TestCase):
    """
    Basic tests of _handle_nulls_and_blanks_from_json
    CASES: all these cases feed None or similar data to _handle_nulls_and_blanks_from_json
    EXPECT: all should return None
    """
    def test_handle_empty_strings(self):
        region = ""

        region_out = _handle_nulls_and_blanks_from_json(region)
        assert not region_out

    def test_handle_blank_space_strings(self):
        region = " "
        
        region_out = _handle_nulls_and_blanks_from_json(region)
        assert not region_out

    def test_handle_literally_none(self):
        region = None
        
        region_out = _handle_nulls_and_blanks_from_json(region)
        assert not region_out


class TestHandleNullsAndBlanks_CasesWithSomeData(TestCase):
    """
    Basic tests of _handle_nulls_and_blanks_from_json
    CASES: all these cases feed a valid string to _handle_nulls_and_blanks_from_json
    EXPECT: all should return a string, with leading/trailing spaces removed if applicable
    """
    def test_spaced_out_string(self):
        region = " a nice string "

        region_out = _handle_nulls_and_blanks_from_json(region)
        assert region_out == "a nice string"

    def test_straightforward_string(self):
        region = "easy string"

        region_out = _handle_nulls_and_blanks_from_json(region)
        assert region_out == region
