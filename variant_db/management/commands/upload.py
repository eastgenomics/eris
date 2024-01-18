"""
python manage.py upload --help
"""
import pathlib
from pathlib import Path
import pandas as pd

from django.core.management.base import BaseCommand
from .populate_db_from_files import var_db_upload_controller


class Command(BaseCommand):
    help = "Command line interface for the variant_db app."

    def add_arguments(self, parser) -> None:
        """Define the source of the data to import."""

        # python manage.py seed --debug panelapp all
        parser.add_argument("--debug", action="store_true", help="run in debug mode")
        subparsers = parser.add_subparsers(dest="command")

        variants = subparsers.add_parser("variants", help="seed variant results files")
        variants.add_argument(
            "directory_path",
            type=str,
            help="Path to a directory containing variants to upload to Eris database",
        )

    def _validate_path(self, directory: str) -> Path:
        """
        Convert the directory to a Pathlib path.
        Throw errors and exit if the path doesn't exist, isn't a directory, or is empty.
        Return the path if it passes.

        :param self:
        :param directory: string containing directory path
        :return: Pathlib Path object
        """
        path = Path(directory)
        if not path.exists() or not path.is_dir():
            print(
                "Directory path doesn't exist, or isn't a real directory - please check and try again"
            )
            exit(1)
        if not any(path.iterdir()):
            print(
                "The provided directory is empty - please provide a directory path which contains data"
            )
            exit(1)
        else:
            return path

    def _basic_file_validity_check(self, file: pathlib.PosixPath) -> pd.DataFrame:
        """
        Check that the file has a sensible name, is parsable to a DataFrame, and
        includes the expected columns.

        :param: file, a pathlib.PosixPath found inside a directory
        :returns: file_table, a Pandas Dataframe containing the file's full contents
        """
        # TODO: check the filename is 'as expected' and the file isn't too big
        # TODO: may want to enforce 'expected' names of files and columns from the workbook parser
        df = pd.read_csv(file, delimiter=",")
        return df

    def handle(self, *args, **kwargs) -> None:
        """
        Handles the command line interface for the variant_db app.
        Currently the only command is: 'python manage.py upload variants <path_to_directory>',
         which lets the user start variant upload of variant-containing files from a specified directory.
        """

        command: str = kwargs.get("command")
        assert command, "Please specify command: variants"

        if command == "variants":
            # Get directory path, and then find any files contained in it or its sub-directories
            directory: str = kwargs.get("directory_path")
            path = self._validate_path(directory)
            p = path.glob("**/*")
            files = [x for x in p if x.is_file()]

            # Work through each file, convert to Pandas DataFrame if valid. Quit out and/or print errors if something is wrong.
            parsed_files = []
            for file in files:
                # TODO: add function to parse all file contents, and add to parsed_files
                parsed_files.append(self._basic_file_validity_check(file))

            # Call the 'main' function which will handle data entry to the database
            var_db_upload_controller(parsed_files)
