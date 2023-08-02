"""
python manage.py generate --help
"""
from requests_app.models import (
    ClinicalIndicationPanel,
    PanelGene,
    Transcript,
)
import os
import re
import csv
import collections
import datetime as dt

from django.core.management.base import BaseCommand
from ._utils import normalize_version
from panel_requests.settings import GENEPANEL_HGNC

ACCEPTABLE_COMMANDS = ["genepanels", "g2t"]


class Command(BaseCommand):
    help = "generate genepanels"

    def _validate_directory(self, path) -> bool:
        """
        Validate if directory exists

        :param path: path to directory

        :return: True if directory exists, False otherwise
        """
        return os.path.exists(path)

    def _validate_hgnc(self, file_path: str) -> bool:
        """
        Validate if hgnc file is valid

        :param file_path: path to hgnc file

        :return: True if hgnc file is valid, False otherwise
        """
        if not os.path.isfile(file_path):
            return False

        with open(file_path, "r") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                if "HGNC ID" not in row:
                    raise ValueError("HGNC ID column not found in HGNC dump")

                if "Locus type" not in row:
                    raise ValueError("Locus Type column not found in HGNC dump")

                if "Approved name" not in row:
                    raise ValueError("Approved Name column not found in HGNC dump")

                break

        return True

    def _parse_hgnc(self, file_path) -> set:
        """
        Parse hgnc file

        Function inspired by https://github.com/eastgenomics/panel_ops/blob/main_without_docker/ops/utils.py#L1251

        :param file_path: path to hgnc file

        :return: set of rnas
        """
        rnas = set()

        with open(file_path, "r") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                # get all rnas
                if re.search(
                    "rna",
                    row["Locus type"],
                    re.IGNORECASE,
                ) or re.search(
                    "mitochondrially encoded",
                    row["Approved name"],
                    re.IGNORECASE,
                ):
                    rnas.add(row["HGNC ID"])

        return rnas

    def _generate_genepanels(self, rnas: set, output_directory: str) -> None:
        """
        Main function to generate genepanel.tsv

        :param rnas: set of rnas
        :param output_directory: output directory
        """
        print("Creating genepanels file")

        ci_panels = collections.defaultdict(list)
        panel_genes = collections.defaultdict(list)
        relevant_panels = set()

        results = []

        if not ClinicalIndicationPanel.objects.filter(current=True).exists():
            # if there's no CiPanelAssociation date column, high chance Test Directory
            # has not been imported yet.
            raise ValueError(
                "Test Directory has yet been imported!"
                "ClinicalIndicationPanel table is empty"
                "python manage.py seed td <td.json>"
            )

        for row in ClinicalIndicationPanel.objects.filter(current=True).values(
            "clinical_indication_id__r_code",
            "clinical_indication_id__name",
            "panel_id",
            "panel_id__panel_name",
            "panel_id__panel_version",
        ):
            relevant_panels.add(row["panel_id"])
            ci_panels[row["clinical_indication_id__r_code"]].append(row)

        for row in PanelGene.objects.filter(panel_id__in=relevant_panels).values(
            "gene_id__hgnc_id", "panel_id"
        ):
            panel_genes[row["panel_id"]].append(row["gene_id__hgnc_id"])

        for r_code, panel_list in ci_panels.items():
            # for each clinical indication
            for panel_dict in panel_list:
                # for each panel associated with that clinical indication
                panel_id: str = panel_dict["panel_id"]
                ci_name: str = panel_dict["clinical_indication_id__name"]
                for hgnc in panel_genes[panel_id]:
                    # for each gene associated with that panel
                    if hgnc in GENEPANEL_HGNC or hgnc in rnas:
                        continue

                    # process the panel version
                    panel_version: str = (
                        normalize_version(panel_dict["panel_id__panel_version"])
                        if panel_dict["panel_id__panel_version"]
                        else "1.0"
                    )

                    results.append(
                        [
                            f"{r_code}_{ci_name}",
                            f"{panel_dict['panel_id__panel_name']}_{panel_version}",
                            hgnc,
                        ]
                    )

        sorted(results, key=lambda x: [x[0], x[1], x[2]])

        current_datetime = dt.datetime.today().strftime("%Y%m%d")

        with open(f"{output_directory}/{current_datetime}_genepanels.tsv", "w") as f:
            for row in results:
                data = "\t".join(row)
                f.write(f"{data}\n")

    def _generate_g2t(self, output_directory) -> None:
        """
        Main function to generate g2t.tsv

        :param output_directory: output directory
        """
        current_datetime = dt.datetime.today().strftime("%Y%m%d")

        with open(
            f"{output_directory}/{current_datetime}_g2t.tsv", "w", newline=""
        ) as f:
            writer = csv.writer(f, delimiter="\t", lineterminator="\n")
            for row in (
                Transcript.objects.order_by("gene_id")
                .all()
                .values("gene_id__hgnc_id", "transcript", "source")
            ):
                hgnc_id = row["gene_id__hgnc_id"]
                transcript = row["transcript"]
                source = row.get("source")

                writer.writerow(
                    [
                        hgnc_id,
                        transcript,
                        "clinical_transcript" if source else "not_clinical_transcript",
                    ]
                )

    def add_arguments(self, parser):
        parser.add_argument("command", nargs="?")
        parser.add_argument("--hgnc")
        parser.add_argument("--output")

    def handle(self, *args, **options):
        """
        Command line handler for python manage.py generate
        """

        cmd = options.get("command")

        # determine if command is valid
        if not cmd or cmd not in ACCEPTABLE_COMMANDS:
            raise ValueError(
                "lack or invalid command argument."
                "Accepted commands: {}".format(ACCEPTABLE_COMMANDS)
            )

        # determine if output directory is specified
        if not options["output"]:
            output_directory = os.getcwd()
            print(
                f"No output directory specified. Using default output directory: {output_directory}"
            )
        else:
            if not self._validate_directory(options["output"]):
                raise ValueError(
                    f'Output directory specified {options["output"]} is not valid. Please use full path'
                )
            output_directory = options["output"]

        # if command is genepanels, then check if hgnc dump is specified
        if cmd == "genepanels" and not options["hgnc"]:
            raise ValueError(
                "No HGNC dump specified e.g. python manage.py generate genepanels --hgnc <path to hgnc dump>"
            )

        # validate if HGNC file given is valid
        if options.get("hgnc") and not self._validate_hgnc(options["hgnc"]):
            raise ValueError(f'HGNC file: {options["hgnc"]} not valid')

        # if command is genepanels, then parse hgnc dump and generate genepanels.tsv
        if cmd == "genepanels" and options.get("hgnc"):
            rnas = self._parse_hgnc(options["hgnc"])

            self._generate_genepanels(rnas, output_directory)

            print(f"Genepanel file created at {output_directory}")

        # if command is g2t, then generate g2t.tsv
        if cmd == "g2t":
            self._generate_g2t(output_directory)
