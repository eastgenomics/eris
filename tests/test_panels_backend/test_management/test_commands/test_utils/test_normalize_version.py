from django.test import TestCase

from panels_backend.management.commands.utils import normalize_version


class TestNormalizeVersion(TestCase):
    def setUp(self) -> None:
        return super().setUp()

    def test_removes_zeros_correctly(self):
        """
        CASE: Version numbers AS STRINGS with decimal-points are provided.
        They contain zero-passing up to 5 spaces, to enable database sorting.
        EXPECT: Zero-padding is removed, regardless of how many 0s are
        used to pad, but trailing 0s are left alone.
        Only one decimal place is tolerated
        """
        with self.subTest():
            zero_after_point_example = "00003.00000"
            zero_after_point_example = "3.0"
            assert (
                normalize_version(zero_after_point_example)
                == zero_after_point_example
            )
        with self.subTest():
            easy_example = "00003.00002"
            easy_expect = "3.2"
            assert normalize_version(easy_example) == easy_expect
        with self.subTest():
            middling_example = "00005.00010"
            middling_expect = "5.10"
            print(normalize_version(middling_example))
            assert normalize_version(middling_example) == middling_expect
        with self.subTest():
            weirder_example = "00006.00010.00005"
            weirder_expect = "6.10.5"
            with self.assertRaises(ValueError):
                assert normalize_version(weirder_example) == weirder_expect
        with self.subTest():
            # None or None-evaluating types are turned into 0.0
            assert normalize_version("") == 0.0
            assert normalize_version(None) == 0.0
