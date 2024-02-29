from django.test import TestCase
from unittest import mock

from panels_backend.management.commands._parse_transcript import (
    _populate_mane_dict_by_category,
)


class TestPopulateManeDictByCategory_ValueError(TestCase):
    """
    Note that we only test 1 case here, because tests for function which
    call '_populate_mane_dict_by_category' have covered the rest of this
    code already.
    CASE: An invalid MANE type is passed
    EXPECT: A ValueError is raised
    """
    def test_value_error(self):
        expected_err = (
            "MANE Type does not match MANE Select or MANE Plus Clinical"
            " - check how mane_data has been set up" 
        )
        with self.assertRaisesRegex(ValueError, expected_err):
            tx = [{"MANE TYPE": "test"}]
            does_version_match = True

            result = _populate_mane_dict_by_category(tx, does_version_match)
