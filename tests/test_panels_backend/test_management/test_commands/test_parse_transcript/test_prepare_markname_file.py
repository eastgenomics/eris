from django.test import TestCase
from panels_backend.management.commands._parse_transcript import prepare_markname_file


class TestPrepareMarknameFile(TestCase):
    """
    Test that _prepare_markname_file returns the expected types
    """

    def setUp(self) -> None:
        self.sample_file_path = "testing_files/eris/sample_markname.csv"

    def test_expected_output_straightforward(self):
        """
        CASE: A very short version of the file is parsed.
        EXPECT: A dictionary containing string-keys with values that are lists of strings.
        """
        expected = {"18222": ["1"], "7": ["2"]}
        result = prepare_markname_file(self.sample_file_path)
        self.assertEqual(expected, result)
