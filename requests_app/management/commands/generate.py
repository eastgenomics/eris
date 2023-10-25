"""
python manage.py generate --help
"""
from requests_app.models import (
    ClinicalIndicationPanel,
    ClinicalIndicationSuperPanel,
    PanelSuperPanel,
    PanelGene,
    Transcript,
)
import os
import csv
import collections
import datetime as dt

from django.core.management.base import BaseCommand
from .utils import normalize_version, parse_hgnc
from panel_requests.settings import HGNC_IDS_TO_OMIT

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
            header: list[str] = [h.rstrip("\n") for h in f.readline().split("\t")]

            assert "HGNC ID" in header, "HGNC ID column not found in HGNC dump"
            assert "Locus type" in header, "Locus Type column not found in HGNC dump"
            assert (
                "Approved name" in header
            ), "Approved Name column not found in HGNC dump"

        return True

    def _get_relevant_ci_panels(self) -> tuple[dict[str, list], set]:
        """
        Retrieve relevant panels and CI-panels from the database
        These will be output in the final file.
        Returns CI panels and a list of relevant panels.

        :return: ci_panels, a dict containing R codes as keys, with lists
        of clinical indication-panel information provided as keys
        :return: relevant_panels [set], a set of relevant panel IDs
        """
        relevant_panels = set()

        ci_panels = collections.defaultdict(list)

        for row in ClinicalIndicationPanel.objects.filter(
            current=True, pending=False
        ).values(
            "clinical_indication_id__r_code",
            "clinical_indication_id__name",
            "panel_id",
            "panel_id__panel_name",
            "panel_id__panel_version",
        ):
            relevant_panels.add(row["panel_id"])
            ci_panels[row["clinical_indication_id__r_code"]].append(row)

        return ci_panels, relevant_panels

    def _get_relevant_ci_superpanels(self) -> tuple[dict[str, list], list]:
        """
        Retrieve relevant superpanels and CI-superpanels from the database
        These will be output in the final file.
        Returns CI superpanels and a list of relevant superpanels.
        
        :return: ci_superpanels, a dict containing R codes as keys, with lists
        of clinical indication-superpanel information provided as keys
        :return: relevant_panels [set], a set of relevant superpanel IDs
        """
        relevant_panels = set()

        ci_panels = collections.defaultdict(list)

        for row in ClinicalIndicationSuperPanel.objects.filter(
            current=True, pending=False
        ).values(
            "clinical_indication__r_code",
            "clinical_indication__name",
            "superpanel__pk",
            "superpanel__panel_name",
            "superpanel__panel_version",
        ):
            relevant_panels.add(row["superpanel__pk"])
            ci_panels[row["clinical_indication__r_code"]].append(row)

        return ci_panels, relevant_panels

    def _get_relevant_panel_genes(self, relevant_panels: list[int]) -> dict[int, str]:
        """
        Using a list of relevant panels,
        retrieve the genes from those panels from the PanelGene database.

        :param: relevant_panels [list[int]], a set of IDs of Panel objects
        which will be used to retrieve those panels' genes from the db
        :returns: panel_genes, a dict containing panel ID as keys and
        gene information in the values
        """
        panel_genes = collections.defaultdict(list)

        for row in PanelGene.objects.filter(
            panel_id__in=relevant_panels,
            active=True,  # only fetch active panel-gene links
        ).values("gene_id__hgnc_id", "panel_id"):
            panel_genes[row["panel_id"]].append(row["gene_id__hgnc_id"])

        return panel_genes

    def _get_relevant_superpanel_genes(
        self, relevant_superpanels: list[int]
    ) -> dict[int, str]:
        """
        Using a list of relevant superpanels,
        first find the constituent panels,
        then retrieve the genes from those panels from the PanelGene database.
        Returns a dict where the key is the superpanel's ID and the values are
        lists of genes.

        :param: relevant_panels [list[int]], a set of IDs of SuperPanel objects
        which will be used to retrieve constituent panels' genes from the db
        :returns: superpanel_genes, a dict containing superpanel ID as keys, and
        gene information for the child-panels in the values
        """
        superpanel_genes = collections.defaultdict(list)

        for superpanel_id in relevant_superpanels:
            linked_panel_list = PanelSuperPanel.objects.filter(
                superpanel__id=superpanel_id
            )
            for i in linked_panel_list:
                genes = PanelGene.objects.filter(panel=i.panel).values(
                    "gene_id__hgnc_id", "panel_id"
                )
                for x in genes:
                    superpanel_genes[superpanel_id].append(x["gene_id__hgnc_id"])

        return superpanel_genes

    def _format_output_data_genepanels(
        self, ci_panels: dict[str, list], panel_genes: dict[int, str], rnas: set
    ) -> list[tuple[str, str, str]]:
        """
        Format a list of results ready for writing out to file.
        Sort the results before returning them.

        :param: ci_panels, a dict linking clinical indications to panels
        :param: panel_genes, a dict linking genes to panel IDs
        :param: rnas, a set of RNAs parsed from HGNC information

        :return: a list-of-lists. Each sublist contains a clinical indication,
        panel name, and panel version
        """
        results = []
        for r_code, panel_list in ci_panels.items():
            # for each clinical indication
            for panel_dict in panel_list:
                # for each panel associated with that clinical indication
                panel_id: str = panel_dict["panel_id"]
                ci_name: str = panel_dict["clinical_indication_id__name"]
                for hgnc in panel_genes[panel_id]:
                    # for each gene associated with that panel
                    if hgnc in HGNC_IDS_TO_OMIT or hgnc in rnas:
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
        results = sorted(results, key=lambda x: [x[0], x[1], x[2]])
        return results

    def _format_output_data_genesuperpanels(
        self, ci_panels: dict[str, list], panel_genes: dict[int, str], rnas: set
    ) -> list[tuple[str, str, str]]:
        """
        Format a list of results ready for writing out to file.
        Sort the results before returning them.

        :param: ci_panels, a dict linking clinical indications to superpanels
        :param: panel_genes, a dict linking genes to superpanel IDs
        :param: rnas, a set of RNAs parsed from HGNC information

        :return: a list-of-lists. Each sublist contains a clinical indication,
        superpanel name, and superpanel version
        """
        results = []
        for r_code, panel_list in ci_panels.items():
            # for each clinical indication
            for panel_dict in panel_list:
                print(panel_dict.keys())

                # for each panel associated with that clinical indication
                panel_id: str = panel_dict["superpanel__pk"]
                ci_name: str = panel_dict["clinical_indication__name"]

                for hgnc in panel_genes[panel_id]:
                    # for each gene associated with that panel
                    if hgnc in HGNC_IDS_TO_OMIT or hgnc in rnas:
                        continue

                    # process the panel version
                    panel_version: str = (
                        normalize_version(panel_dict["superpanel__panel_version"])
                        if panel_dict["superpanel__panel_version"]
                        else "1.0"
                    )
                    results.append(
                        [
                            f"{r_code}_{ci_name}",
                            f"{panel_dict['superpanel__panel_name']}_"
                            f"{panel_version}",
                            hgnc,
                        ]
                    )
        results = sorted(results, key=lambda x: [x[0], x[1], x[2]])
        return results

    def _generate_genepanels(self, rnas: set, output_directory: str) -> None:
        """
        Main function to generate genepanel.tsv
        Runs sanity checks, then calls a formatter if these pass
        Outputs formatted data
        :param rnas: set of rnas
        :param output_directory: output directory
        """
        print("Creating genepanels file")

        if not ClinicalIndicationPanel.objects.filter(
            current=True, pending=False
        ).exists():
            # if there's no CiPanelAssociation date column, high chance Test Directory
            # has not been imported yet.
            raise ValueError(
                "Test Directory has not yet been imported!"
                "ClinicalIndicationPanel table is empty"
                "python manage.py seed td <td.json>"
            )

        # block generation of genepanel.tsv if ANY data is awaiting review (pending=True)
        if ClinicalIndicationPanel.objects.filter(pending=True).exists():
            raise ValueError(
                "Some ClinicalIndicationPanel table values require manual review. "
                "Please resolve these through the review platform and try again."
            )

        # block generation of genepanel.tsv if ANY data is awaiting review
        # (pending=True)
        if ClinicalIndicationSuperPanel.objects.filter(pending=True).exists():
            raise ValueError(
                "Some ClinicalIndicationSuperPanel table values require "
                "manual review. Please resolve these through the review "
                "platform and try again."
            )

        ci_panels, relevant_panels = self._get_relevant_ci_panels()
        ci_superpanels, relevant_superpanels = self._get_relevant_ci_superpanels()

        panel_genes = self._get_relevant_panel_genes(relevant_panels)
        superpanel_genes = self._get_relevant_superpanel_genes(relevant_superpanels)

        panel_results = self._format_output_data_genepanels(
            ci_panels, panel_genes, rnas
        )
        superpanel_results = self._format_output_data_genesuperpanels(
            ci_superpanels, superpanel_genes, rnas
        )

        results = panel_results + superpanel_results

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

        print("Creating g2t file")

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

    def add_arguments(self, parser) -> None:
        """
        Define parsers for generate command
        Default function in Django
        """

        # main parser: genepanels or g2t
        parser.add_argument("command", nargs="?")
        # optional parser for hgnc dump
        # mandatory for genepanels generation but not for g2t

        parser.add_argument("--hgnc")

        # optional parser for output directory
        parser.add_argument("--output")

    def handle(self, *args, **kwargs):
        """
        Command line handler for python manage.py generate
        e.g.
        python manage.py generate genepanels --hgnc <hgnc dump>
        python manage.py generate g2t --output <output directory>

        """

        cmd = kwargs.get("command")

        # determine if command is valid
        if not cmd or cmd not in ACCEPTABLE_COMMANDS:
            raise ValueError(
                "lack or invalid command argument."
                "Accepted commands: {}".format(ACCEPTABLE_COMMANDS)
            )

        # determine if output directory is specified
        if not kwargs["output"]:
            output_directory = os.getcwd()
            print(
                f"No output directory specified. Using default output directory: {output_directory}"
            )
        else:
            if not self._validate_directory(kwargs["output"]):
                raise ValueError(
                    f'Output directory specified {kwargs["output"]} is not valid. Please use full path'
                )
            output_directory = kwargs["output"]

        # if command is genepanels, then check if hgnc dump is specified
        if cmd == "genepanels" and not kwargs["hgnc"]:
            raise ValueError(
                "No HGNC dump specified e.g. python manage.py generate genepanels --hgnc <path to hgnc dump>"
            )

        # validate if HGNC file given is valid
        if kwargs.get("hgnc") and not self._validate_hgnc(kwargs["hgnc"]):
            raise ValueError(f'HGNC file: {kwargs["hgnc"]} not valid')

        # if command is genepanels, then parse hgnc dump and generate genepanels.tsv
        if cmd == "genepanels" and kwargs.get("hgnc"):
            rnas = parse_hgnc(kwargs["hgnc"])

            self._generate_genepanels(rnas, output_directory)

            print(f"Genepanel file created at {output_directory}")

        # if command is g2t, then generate g2t.tsv
        if cmd == "g2t":
            self._generate_g2t(output_directory)

            print(f"g2t file created at {output_directory}")
