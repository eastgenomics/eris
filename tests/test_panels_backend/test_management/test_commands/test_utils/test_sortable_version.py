from django.test import TestCase

from panels_backend.management.commands.utils import sortable_version


class TestSortableVersion(TestCase):
    def setUp(self) -> None:
        return super().setUp()
    
    def test_pads_correctly(self):
        """
        CASE: Version numbers AS STRINGS with decimal-points are provided
        EXPECT: The numbers with decimals are zero-padded up to 5 spaces,
        regardless of how many decimals there are
        """
        with self.subTest():
            easy_example = "3.2"
            easy_expect = "00003.00002"
            assert sortable_version(easy_example) == easy_expect
        with self.subTest():
            middling_example = "5.10"
            middling_expect = "00005.00010"
            assert sortable_version(middling_example) == middling_expect
        with self.subTest():
            weirder_example = "6.10.5"
            weirder_expect = "00006.00010.00005"
            assert sortable_version(weirder_example) == weirder_expect
