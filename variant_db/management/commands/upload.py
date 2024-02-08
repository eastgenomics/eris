"""
python manage.py upload --help
"""
import logging
import pandas as pd

from django.db import DatabaseError
from django.core.management.base import BaseCommand
from .controller import upload

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.INFO)


class Command(BaseCommand):
    help = "Command line interface for the variant_db app."

    def add_arguments(self, parser) -> None:
        """Define the source of the data to import."""

        # python manage.py seed --debug panelapp all
        parser.add_argument("--debug", action="store_true", help="run in debug mode")
        subparsers = parser.add_subparsers(dest="command")

        # python manage.py upload variants
        variants = subparsers.add_parser("variants", help="seed variant results files")
        variants.add_argument(
            "-w",
            "--workbooks",
            type=str,
            nargs="+",
            required=True,
            help="One or more filepaths to variant workbook files",
        )

    def handle(self, *args, **options) -> None:
        """
        Handles the command line interface for the variant_db app.
        Currently the only command is: 'python manage.py upload variants --workbooks=*.csv',
        which lets the user start variant upload of variant-containing files.
        """
        if options["command"] == "variants":
            for workbook in options["workbooks"]:
                logging.info(
                    f"===============\n\nWorkbook {workbook}: attempting upload"
                )
                try:
                    upload(workbook)
                except DatabaseError as e:
                    logging.error(
                        f"Workbook {workbook}:\n\
                                  Exception raised: {e}.\n\
                                  Rolling back transactions and continuing to next workbook"
                    )
                    continue
                except KeyError as e:
                    logging.error(
                        f"Workbook: {workbook}\n\
                                  Exception raised: {e}\n\
                                  It is likely that your headers don't conform to the specs. Please seek advice from a bioinformatics manager\n\
                                  Rolling back transactions and continuing to next workbook"
                    )
                    continue
                except ValueError as e:
                    logging.error(
                        f"Workbook: {workbook}\nException raised: {e}\n\
                                  It is likely that a value(s) are an invalid type. Please seek advice from a bioinformatics manager\n\
                                  Rolling back transactions and moving to next workbook"
                    )
                    continue
                else:
                    logging.info(f"Workbook {workbook} uploaded successfully")
        else:
            logging.info("Done")
            exit(1)
