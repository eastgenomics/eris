"""
python manage.py upload --help
"""
import glob
import logging
import pandas as pd

from django.core.management.base import BaseCommand
from .controller import upload


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
                upload(workbook)
        else:
            exit(1)
