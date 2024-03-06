from django.test import TestCase
from unittest import mock
from unittest.mock import patch, mock_open
from datetime import date

from panels_backend.management.commands.generate import (
    Command,
)


class TestWriteGenepanels(TestCase):
    """
    Test that gene panels write out to file in the correct format
    """

    def test_standard_results(self):
        """
        CASE: A basic, short set of genepanel results, containing non-null
        values for each tuple entry, are passed to the writer function.
        EXPECT: The output file gets an appropriately-dated name. It writes
        to the specified output directory. Every tuple is turned into
        a row in the file.
        """
        command = Command()
        test_input = [
            tuple(
                [
                    "R120_A clinical indication",
                    "Panel name_4.0",
                    "HGNC:456",
                    "125",
                ]
            )
        ]

        with patch("builtins.open", mock_open()) as write_out:
            with patch(
                "panels_backend.management.commands.generate.date"
            ) as mock_date:
                mock_date.today.return_value = date(2024, 2, 19)
                mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

                output_dir = "/dev/null"
                command._write_genepanels_results(test_input, output_dir)

                # check the correct file name is written to
                with self.subTest():
                    write_out.assert_called_once_with(
                        "/dev/null/20240219_genepanels.tsv", "w"
                    )

                # check expected contents are written to file
                with self.subTest():
                    write_out.assert_has_calls(
                        [
                            mock.call().write(
                                "R120_A clinical indication\tPanel name_4.0"
                                "\tHGNC:456\t125\n"
                            ),
                        ]
                    )
