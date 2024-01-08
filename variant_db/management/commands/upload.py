"""
python manage.py upload --help
"""

from pathlib import Path
import re

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Command line interface for the variant_db app."
    )

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
            print("Directory path doesn't exist, or isn't a real directory - please check and try again")
            exit(1)
        if not any(path.iterdir()):
            print("The provided directory is empty - please provide a directory path which contains data")
            exit(1)
        else:
            return path
        
    
    def _fetch_var_files(self, directory):
        """
        """
        #TODO: iter through files in directory, and add to an output list
        return directory


    def handle(self, *args, **kwargs) -> None:
        """
        Handles the command line interface for the variant_db app.
        Currently the only command is: 'python manage.py upload variants <path_to_directory>',
         which lets the user start variant upload from a specified directory.
        """

        command: str = kwargs.get("command")
        assert command, "Please specify command: variants"

        if command == "variants":
            # Get directory ath
            directory: str = kwargs.get("directory_path")
            path = self._validate_path(directory)
            files = self._fetch_var_files(path)
            #TODO: add function to parse all file contents


