"""
python manage.py seed --help
"""

import os
import json
import re

from ._insert_panel import panel_insert_controller
from ._parse_transcript import seed_transcripts
from ._insert_ci import insert_test_directory_data
from .panelapp import get_panel, PanelClass, fetch_all_panels


from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Coordinate the functions in other scripts to import and "
        "parse data, then use insert.py to insert the cleaned data into "
        "the database."
    )

    def _validate_td(self, directory: str) -> bool:
        """Validate that the input file is a json file and is there"""
        if not directory.endswith(".json") or not os.path.isfile(directory):
            return False

        return True

    def _validate_file_exist(self, file_paths: list[str]) -> bool:
        """Validate that the input files are there"""
        missing_files: list[str] = []

        for file_path in file_paths:
            if not file_path or not os.path.isfile(file_path):
                missing_files.append(file_path)

        if missing_files:
            raise Exception(f"Files {', '.join(missing_files)} do not exist")

        return True

    def _validate_ext_ids(self, file_ids: list[str]) -> None:
        """
        Validate that the external file ids are in the correct format
        :param: file_ids, a list of file ID strings
        """

        missing_ids = [id for id in file_ids if not re.match(r"^file-[\w]+$", id)]

        if missing_ids:
            raise Exception(
                f"External file IDs {', '.join(missing_ids)} are misformatted,"
                f" file IDs must take the format 'file-' followed by an alphanumerical string"
            )

    def _validate_release_versions(self, releases: list[str]) -> None:
        """
        Validate that the external releases are in the correct format
        Only numbers and dots are permitted, e.g. 1.0.13
        """

        invalid_releases = [id for id in releases if not re.match(r"^\d+(\.\d+)*$", id)]

        if invalid_releases:
            raise Exception(
                f"The release versions {', '.join(invalid_releases)} are misformatted, "
                f"release versions may only contain numbers and dots"
            )

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
            "--td_release",
            type=str,
            help="The documented release version of the test directory file",
            required=True,
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
            "--hgnc_release",
            type=str,
            help="The documented release version of the HGNC file",
            required=True,
        )
        transcript.add_argument(
            "--mane",
            type=str,
            help="Path to mane .csv file",
            default="testing_files/mane_grch37.csv",
        )
        transcript.add_argument(
            "--mane_ext_id",
            type=str,
            help="The DNAnexus file ID of the MANE .csv file. Will start with 'file-'",
            required=True,
        )
        transcript.add_argument(
            "--mane_release",
            type=str,
            help="The documented release version of the MANE file(s)",
            required=True,
        )
        transcript.add_argument(
            "--gff",
            type=str,
            help="Path to parsed gff .tsv file",
            default="testing_files/GCF_000001405.25_GRCh37.p13_genomic.exon_5bp_v2.0.0.tsv",
        )
        transcript.add_argument(
            "--gff_release",
            type=str,
            help="The documented release version of the GFF file",
            required=True,
        )
        transcript.add_argument(
            "--g2refseq",
            type=str,
            help="Path to gene2refseq csv file",
            default="testing_files/gene2refseq_202306131409.csv",
        )
        transcript.add_argument(
            "--g2refseq_ext_id",
            type=str,
            help="The file ID of the gene2refseq csv file. Will start with 'file-'",
            required=True,
        )
        transcript.add_argument(
            "--markname",
            type=str,
            help="Path to markname csv file",
            default="testing_files/markname_202306131409.csv",
        )
        transcript.add_argument(
            "--markname_ext_id",
            type=str,
            help="The file ID of the markname csv file. Will start with 'file-'",
            required=True,
        )
        transcript.add_argument(
            "--hgmd_release",
            type=str,
            help="The documented release version of the HGMD files",
            required=True,
        )
        transcript.add_argument(
            "--error",
            action="store_true",
            help="write error log for transcript seeding",
        )
        transcript.add_argument(
            "--refgenome",
            type=str,
            help="Reference Genome",
            required=True,
        )

    def handle(self, *args, **kwargs) -> None:
        """Coordinates functions to import and parse data from
        specified source, then calls inserter to insert cleaned data
        into the database."""

        test_mode: bool = kwargs.get("debug", False)
        command: str = kwargs.get("command")

        assert command, "Please specify command: panelapp / td / transcript"

        # TODO: fill user variable from somewhere more appropriate, like a database table
        user = "init_v1_user"

        # python manage.py seed panelapp <all/panel_id> <version>
        if command == "panelapp":
            panel_id: str = kwargs.get("panel")
            panel_version: str = kwargs.get("version")

            if panel_id == "all":
                panels, superpanels = fetch_all_panels()
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
                panel_data, is_superpanel = get_panel(panel_id, panel_version)

                if not panel_data:
                    print(
                        f"Fetching panel id: {panel_id} version: {panel_version} failed"
                    )
                    raise ValueError("Panel specified does not exist")
                panel_data.panel_source = "PanelApp"  # manual addition of source

                if is_superpanel:
                    panels = []
                    superpanels = [panel_data]
                else:
                    panels = [panel_data]
                    superpanels = []

            if not test_mode:
                # not printing amounts because there are some duplicates now,
                # due to how superpanels work
                print(f"Importing panels into database...")

                # insert panel data into database
                panel_insert_controller(panels, superpanels, user)

                print("Done.")

        # python manage.py seed td <input_json> --td_release <td_release_version> <Y/N>
        elif command == "td":
            input_directory = kwargs.get("input")
            td_release = kwargs.get("td_release")
            force: bool = kwargs.get("force")

            if not self._validate_td(input_directory):
                raise ValueError("Invalid input file")

            self._validate_release_versions([td_release])

            with open(input_directory) as reader:
                json_data = json.load(reader)

            if not test_mode:
                insert_test_directory_data(json_data, td_release, force)

        # python manage.py seed transcript --hgnc <path> --hgnc_release <str> --mane <path>
        # --mane_ext_id <str> --mane_release <str> --gff <path> --gff_release <str> --g2refseq <path>
        # --g2refseq_ext_id <str> --markname <path> --markname_ext_id <str>
        # --hgmd_release <str> --refgenome <ref_genome_version> --error
        elif command == "transcript":
            """
            This seeding requires the following files and strings:
            1. hgnc dump - with HGNC ID, Approved Symbol, Previous Symbols, Alias Symbols
            2. hgnc release - the in-house release version assigned to the HGNC file
            3. MANE file csv (http://tark.ensembl.org/web/mane_GRCh37_list/)
            4. MANE file's external ID (e.g. in DNAnexus)
            5. MANE release version
            6. parsed gff file on DNAnexus (project-Fkb6Gkj433GVVvj73J7x8KbV:file-GF611Z8433Gk7gZ47gypK7ZZ)
            7. gff release - the in-house release version assigned to the GFF file
            8. gene2refseq table from HGMD database
            9. gene2refseq table's external ID
            10. markname table from HGMD database
            11. markname table's the external ID
            12. hgmd release - in-house label assigned to this version of the data dump
            13. reference genome - e.g. 37/38
            """

            # fetch input reference genome - case sensitive
            ref_genome = kwargs.get("refgenome")

            print("Seeding transcripts")

            hgnc_file = kwargs.get("hgnc")
            hgnc_release = kwargs.get("hgnc_release")
            mane_file = kwargs.get("mane")
            mane_ext_id = kwargs.get("mane_ext_id")
            mane_release = kwargs.get("mane_release")
            gff_file = kwargs.get("gff")
            gff_release = kwargs.get("gff_release")
            g2refseq_file = kwargs.get("g2refseq")
            g2refseq_ext_id = kwargs.get("g2refseq_ext_id")
            markname_file = kwargs.get("markname")
            markname_ext_id = kwargs.get("markname_ext_id")
            hgmd_release = kwargs.get("hgmd_release")

            self._validate_file_exist(
                [
                    hgnc_file,
                    mane_file,
                    gff_file,
                    g2refseq_file,
                    markname_file,
                ]
            )

            self._validate_ext_ids([mane_ext_id, g2refseq_ext_id, markname_ext_id])

            self._validate_release_versions(
                [hgnc_release, mane_release, gff_release, hgmd_release]
            )

            error_log = kwargs.get("error_log", False)

            seed_transcripts(
                hgnc_file,
                hgnc_release,
                mane_file,
                mane_ext_id,
                mane_release,
                gff_file,
                gff_release,
                g2refseq_file,
                g2refseq_ext_id,
                markname_file,
                markname_ext_id,
                hgmd_release,
                ref_genome,
                error_log,
            )

            print("Seed transcripts completed.")
