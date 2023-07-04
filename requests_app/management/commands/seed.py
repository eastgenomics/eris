"""
python manage.py seed --help
"""

import os
import json

from ._parse_pa import parse_specified_pa_panels, parse_all_pa_panels
from ._insert_panel import insert_data_into_db, insert_form_data
from ._parse_transcript import seed_transcripts
from ._insert_ci import insert_data
from ._parse_form import FormParser


from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Coordinate the functions in other scripts to import and "
        "parse data, then use insert.py to insert the cleaned data into "
        "the database."
    )

    def _validate_td(self, directory: str) -> bool:
        if not directory.endswith(".json") or not os.path.isfile(directory):
            return False

        return True

    def add_arguments(self, parser) -> None:
        """Define the source of the data to import."""

        # python manage.py seed --debug panelapp all
        parser.add_argument("--debug", action="store_true", help="debug mode")

        subparsers = parser.add_subparsers(dest="command")

        # Parser for panelapp command e.g. panelapp all or panelapp 1234
        panelapp = subparsers.add_parser("panelapp", help="seed PanelApp data")
        panelapp.add_argument(
            "panel",
            type=str,
            help="PanelApp panel id or all e.g. 1234 or all",
        )

        panelapp.add_argument(
            "version",
            type=str,
            nargs="?",
            default=None,
            help="PanelApp panel version (optional)",
        )

        # Parser for test directory command e.g. test_dir <input_json> <Y/N>
        td = subparsers.add_parser("td", help="import test directory data")

        td.add_argument(
            "input",
            type=str,
            help="Path to JSON file of parsed TD data",
        )

        # TODO: deal with this
        # Parser for form command e.g. form <input_file>
        form = subparsers.add_parser("form", help="import request form data")

        form.add_argument("input", type=str, help="Path to request form file")

        # Parser for transcript command e.g. transcript
        transcript = subparsers.add_parser(
            "transcript", help="seed transcripts for genes"
        )
        transcript.add_argument(
            "--hgnc",
            type=str,
            help="Path to hgnc dump .txt file",
            required=True,
        )
        transcript.add_argument(
            "--mane", type=str, help="Path to mane .csv file", required=True
        )
        transcript.add_argument(
            "--gff",
            type=str,
            help="Path to parsed gff .tsv file",
            required=True,
        )
        transcript.add_argument(
            "--g2refseq",
            type=str,
            help="Path to gene2refseq csv file",
            required=True,
        )
        transcript.add_argument(
            "--markname",
            type=str,
            help="Path to markname csv file",
            required=True,
        )

        transcript.add_argument(
            "--error",
            action="store_true",
            help="write error log for transcript seeding",
        )

    def parse_form_data(self, filepath: str):
        """Use parse_form.py to import and parse data from a panel
        request form.

        args:
            filepath [str]: path to request form file

        returns:
            parsed_data [dict]: data to insert into db
        """

        print("Parsing request form...")

        parser = FormParser(filepath=filepath)

        info, panel_df, gene_df, region_df = parser.get_form_data(filepath)

        # Currently only support 1 panel per form
        if panel_df.shape[0] != 1:
            raise ValueError("Panel data in xlsx not in correct format")

        info_dict = parser.setup_output_dict(info, panel_df)
        info_dict = parser.parse_genes(info_dict, gene_df)
        parsed_data = parser.parse_regions(info_dict, region_df)

        print("Form parsing completed.")

        return parsed_data

    def handle(self, *args, **kwargs) -> None:
        """Coordinates functions to import and parse data from
        specified source, then calls inserter to insert cleaned data
        into the database."""

        print(kwargs)

        test_mode: bool = kwargs.get("debug", False)
        command: str = kwargs.get("command")

        assert command, "Please specify command: panelapp / td / form / transcript"

        # python manage.py seed panelapp <all/panel_id> <version>
        if command == "panelapp":
            panel_id: str = kwargs.get("panel")
            panel_version: str = kwargs.get("version")  # TODO: version not used yet?

            if not panel_id:
                raise ValueError("Please specify panel id")

            if not panel_version:
                raise ValueError("Please specify panel version")

            if panel_id == "all":
                parsed_data = parse_all_pa_panels()
            else:
                # parse data from requested current PanelApp panels
                parsed_data = parse_specified_pa_panels(panel_id)
                if not parsed_data:
                    print("Parsing failed - see error messages.")

            if not test_mode:
                print("Importing panels into database...")

                # insert panel data into database
                for panel_dict in parsed_data:
                    if panel_dict:
                        insert_data_into_db(panel_dict)

                print("Done.")

        # python manage.py seed td <input_json> <Y/N>
        elif command == "td":
            input_directory = kwargs.get("input")

            if not self._validate_td(input_directory):
                raise ValueError("Invalid input file")

            with open(input_directory) as reader:
                json_data = json.load(reader)

            if not test_mode:
                insert_data(json_data)

        # python manage.py seed form <input_file>
        elif command == "form":
            # TODO: This functionality is not usable yet
            # read in data from the form

            form_input = kwargs.get("input")

            parsed_data = self.parse_form_data(form_input)

            if not test_mode:
                insert_form_data(parsed_data)

        # python manage.py seed transcript --hgnc <path> --mane <path> --gff <path> --g2refseq <path> --markname <path> --error
        elif command == "transcript":
            """
            This seeding requires the following files:
            1. hgnc dump - with HGNC ID, Approved Symbol, Previous Symbols, Alias Symbols
            2. MANE file grch37 csv (http://tark.ensembl.org/web/mane_GRCh37_list/)
            3. parsed gff file on DNAnexus (project-Fkb6Gkj433GVVvj73J7x8KbV:file-GF611Z8433Gk7gZ47gypK7ZZ)
            4. gene2refseq table from HGMD database
            5. markname table from HGMD database
            """

            hgnc_file = kwargs.get("hgnc")
            mane_file = kwargs.get("mane")
            gff_file = kwargs.get("gff")
            g2refseq_file = kwargs.get("g2refseq")
            markname_file = kwargs.get("markname")
            error_log = kwargs.get("error_log", False)

            seed_transcripts(
                hgnc_file,
                mane_file,
                gff_file,
                g2refseq_file,
                markname_file,
                error_log,
            )