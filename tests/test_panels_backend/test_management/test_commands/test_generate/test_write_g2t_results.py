from django.test import TestCase
from unittest import mock
from unittest.mock import patch, mock_open
from datetime import date

from panels_backend.management.commands.generate import (
    Command,
)


class TestWriteG2tResults(TestCase):
    """
    Check that results are written to a mock file.
    """

    def test_basic_file(self):
        """
        CASE: A basic, short set of g2t results containing a value for
        every key, are passed to the writer function.
        EXPECT: The output file gets an appropriately-dated name. It writes
        to the specified output directory. Every dictionary is turned into
        a row in the file.
        """
        command = Command()
        test_input = [
            {
                "hgnc_id": "HGNC:1",
                "transcript": "NM123.5",
                "clinical": "clinical_transcript",
            },
            {
                "hgnc_id": "HGNC:1",
                "transcript": "NM0034.1",
                "clinical": "not_clinical_transcript",
            },
        ]
        with patch("builtins.open", mock_open()) as write_out:
            with patch("panels_backend.management.commands.generate.date") as mock_date:
                mock_date.today.return_value = date(2024, 2, 19)
                mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

                command._write_g2t_results(test_input, "/dev/null")

                # check the correct file name is written to
                with self.subTest():
                    write_out.assert_called_once_with(
                        "/dev/null/20240219_g2t.tsv", "w", newline=""
                    )

                # check expected contents are written to file
                with self.subTest():
                    write_out.assert_has_calls(
                        [
                            mock.call().write(
                                "HGNC:1\tNM123.5\tclinical_transcript\n"
                            ),
                            mock.call().write(
                                "HGNC:1\tNM0034.1\tnot_clinical_transcript\n"
                            ),
                        ]
                    )
