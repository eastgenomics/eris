"""
python manage.py seed --help
"""

import os
import json

from ._insert_panel import insert_data_into_db, insert_form_data
from ._parse_transcript import seed_transcripts
from ._insert_ci import insert_data
from .panel import get_panel, PanelClass, fetch_all_panels


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

    def _validate_file_exist(self, file_paths: list[str]) -> bool:
        for file_path in file_paths:
            if not file_path or not os.path.isfile(file_path):
                raise Exception(f"File {file_path} does not exist")

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

        td.add_argument(
            "--force",
            action="store_true",
            help="force td seed ignoring td version",
        )

        # Parser for transcript command e.g. transcript
        transcript = subparsers.add_parser(
            "transcript", help="seed transcripts for genes"
        )
        transcript.add_argument(
            "--hgnc",
            type=str,
            help="Path to hgnc dump .txt file",
            default="testing_files/hgnc_dump_20230613.txt",
        )
        transcript.add_argument(
            "--mane",
            type=str,
            help="Path to mane .csv file",
            default="testing_files/mane_grch37.csv",
        )
        transcript.add_argument(
            "--gff",
            type=str,
            help="Path to parsed gff .tsv file",
            default="testing_files/GCF_000001405.25_GRCh37.p13_genomic.exon_5bp_v2.0.0.tsv",
        )
        transcript.add_argument(
            "--g2refseq",
            type=str,
            help="Path to gene2refseq csv file",
            default="testing_files/gene2refseq_202306131409.csv",
        )
        transcript.add_argument(
            "--markname",
            type=str,
            help="Path to markname csv file",
            default="testing_files/markname_202306131409.csv",
        )

        transcript.add_argument(
            "--error",
            action="store_true",
            help="write error log for transcript seeding",
        )

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

            if panel_id == "all":
                panels: list[PanelClass] = fetch_all_panels()

            else:
                if not panel_id:
                    raise ValueError("Please specify panel id")

                if not panel_version:
                    print("Getting latest panel version")
                else:
                    print(
                        f"Getting panel id {panel_id} / panel version {panel_version}"
                    )

                # parse data from requested current PanelApp panels
                panel = get_panel(panel_id, panel_version)

                if not panel:
                    print(
                        f"Fetching panel id: {panel_id} version: {panel_version} failed"
                    )
                    raise ValueError("Panel specified does not exist")
                panel.panel_source = "PanelApp"  # manual addition of source

                panels = [panel]

            if not test_mode:
                print(f"Importing {len(panels)} panels into database...")

                # insert panel data into database
                for panel in panels:
                    insert_data_into_db(panel)

                print("Done.")

        # python manage.py seed td <input_json> <Y/N>
        elif command == "td":
            input_directory = kwargs.get("input")
            force: bool = kwargs.get("force")

            if not self._validate_td(input_directory):
                raise ValueError("Invalid input file")

            with open(input_directory) as reader:
                json_data = json.load(reader)

            if not test_mode:
                insert_data(json_data, force)

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

            self._validate_file_exist(
                [
                    hgnc_file,
                    mane_file,
                    gff_file,
                    g2refseq_file,
                    markname_file,
                ]
            )

            error_log = kwargs.get("error_log", False)

            seed_transcripts(
                hgnc_file,
                mane_file,
                gff_file,
                g2refseq_file,
                markname_file,
                error_log,
            )
