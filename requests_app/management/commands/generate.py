"""
python manage.py generate --help
"""
from requests_app.models import (
    ClinicalIndicationPanel,
    ClinicalIndicationSuperPanel,
    CiPanelTdRelease,
    CiSuperpanelTdRelease,
    PanelSuperPanel,
    PanelGene,
    Transcript,
    TranscriptRelease,
    TranscriptReleaseTranscript,
    TestDirectoryRelease,
    ReferenceGenome,
)
import os
import csv
import collections
import datetime as dt

from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from .utils import normalize_version, parse_hgnc
from core.settings import HGNC_IDS_TO_OMIT
from ._parse_transcript import _parse_reference_genome, _get_latest_transcript_release
from ._insert_ci import _fetch_latest_td_version

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

    def _get_relevant_ci_panels(self, td_release) -> tuple[dict[str, list], set]:
        """
        Retrieve relevant panels and CI-panels from the database
        These will be output in the final file.
        Returns CI panels and a list of relevant panels.

        :param: td_release, the TestDirectoryRelease table entry for the most-recent test dir version

        :return: ci_panels, a dict containing R codes as keys, with lists
        of clinical indication-panel information provided as keys
        :return: relevant_panels [set], a set of relevant panel primary IDs
        """
        relevant_panels = set()

        ci_panels = collections.defaultdict(list)

        # find Ci-Panels linked to the latest test directory
        for row in CiPanelTdRelease.objects.filter(
            td_release=td_release, ci_panel__current=True, ci_panel__pending=False
        ).values(
            "ci_panel__clinical_indication__r_code",
            "ci_panel__clinical_indication_id__name",
            "ci_panel__panel_id",
            "ci_panel__panel__external_id",
            "ci_panel__panel__panel_name",
            "ci_panel__panel__panel_version",
        ):
            relevant_panels.add(row["ci_panel__panel_id"])
            ci_panels[row["ci_panel__clinical_indication__r_code"]].append(row)

        return ci_panels, relevant_panels

    def _get_relevant_ci_superpanels(self, td_release) -> tuple[dict[str, list], list]:
        """
        Retrieve relevant superpanels and CI-superpanels from the database
        These will be output in the final file.
        Returns CI superpanels and a list of relevant superpanels.

        :param: td_release, the TestDirectoryRelease table entry for the most-recent test dir version

        :return: ci_superpanels, a dict containing R codes as keys, with lists
        of clinical indication-superpanel information provided as keys
        :return: relevant_panels [set], a set of relevant superpanel primary IDs
        """
        relevant_panels = set()

        ci_panels = collections.defaultdict(list)

        for row in CiSuperpanelTdRelease.objects.filter(
            td_release=td_release,
            ci_superpanel__current=True,
            ci_superpanel__pending=False,
        ).values(
            "ci_superpanel__clinical_indication__r_code",
            "ci_superpanel__clinical_indication__name",
            "ci_superpanel__superpanel",
            "ci_superpanel__superpanel__external_id",
            "ci_superpanel__superpanel__panel_name",
            "ci_superpanel__superpanel__panel_version",
        ):
            relevant_panels.add(row["ci_superpanel__superpanel"])
            ci_panels[row["ci_superpanel__clinical_indication__r_code"]].append(row)

        return ci_panels, relevant_panels

    def _get_relevant_panel_genes(self, relevant_panels: list[int]) -> dict[int, str]:
        """
        Using a list of relevant panels,
        retrieve the genes from those panels from the PanelGene database.
        Skip genes that are Pending, or not Active.
        
        :param: relevant_panels [list[int]], a set of IDs of Panel objects
        which will be used to retrieve those panels' genes from the db
        :returns: panel_genes, a dict containing panel ID as keys and
        gene information in the values
        """
        panel_genes = collections.defaultdict(list)

        for row in PanelGene.objects.filter(
            panel__pk__in=relevant_panels,
            active=True,
            pending=False # only fetch active, not-pending panel-gene links
        ).values("gene__hgnc_id", "panel__id"):
            panel_genes[row["panel__id"]].append(row["gene__hgnc_id"])

        return panel_genes

    def _get_relevant_superpanel_genes(
        self, relevant_superpanels: list[int]
    ) -> dict[int, str]:
        """
        Using a list of relevant superpanels, first find the constituent panels,
        then retrieve the genes from those panels from the PanelGene database.

        Returns a dict where the key is the superpanel's ID and the values are
        lists of genes.

        :param: relevant_panels [list[int]], a set of IDs of SuperPanel objects
        which will be used to retrieve constituent panels' genes from the db
        :returns: superpanel_genes, a dict containing superpanel ID as keys, and
        gene information for the child-panels in the values
        """
        # set prevents duplicates
        superpanel_genes = collections.defaultdict(set)

        for superpanel_id in relevant_superpanels:
            # find all linked panels and add their ids to a list
            constituent_panels = []
            for linked_panel in PanelSuperPanel.objects.filter(
                superpanel__id=superpanel_id
            ).values("panel__id"):
                constituent_panels.append(linked_panel["panel__id"])
            
            # for the linked panels, get linked genes, link to SuperPanel's ID
            panels_genes = self._get_relevant_panel_genes(constituent_panels)
            for panel_id, genes in panels_genes.items():
                for gene in genes:
                    superpanel_genes[superpanel_id].add(gene)

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
                panel_id: str = panel_dict["ci_panel__panel__external_id"]
                ci_name: str = panel_dict["ci_panel__clinical_indication_id__name"]
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

    # TODO: test
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
                # for each panel associated with that clinical indication
                panel_id: str = panel_dict["ci_superpanel__superpanel__pk"]
                ci_name: str = panel_dict["ci_superpanel__clinical_indication__name"]

                for hgnc in panel_genes[panel_id]:
                    # for each gene associated with that panel
                    if hgnc in HGNC_IDS_TO_OMIT or hgnc in rnas:
                        continue

                    # process the panel version
                    panel_version: str = (
                        normalize_version(
                            panel_dict["ci_superpanel__superpanel__panel_version"]
                        )
                        if panel_dict["ci_superpanel__superpanel__panel_version"]
                        else "1.0"
                    )
                    results.append(
                        [
                            f"{r_code}_{ci_name}",
                            f"{panel_dict['ci_superpanel__superpanel__panel_name']}_"
                            f"{panel_version}",
                            hgnc,
                        ]
                    )
        results = sorted(results, key=lambda x: [x[0], x[1], x[2]])
        return results

    # TODO: test _block_genepanels
    def _block_genepanels_if_db_not_ready(self) -> str | None:
        """
        Check that there's no Pending data in tables linking CIs to panels,
        and check that the db contains at least some Clinical Indications.
        If this is the case, return a formatted error message.
        If there are no issues, return None.

        :return: error - string or None
        """
        errors = []
        if not ClinicalIndicationPanel.objects.filter(
            current=True, pending=False
        ).exists():
            # if there's no CiPanelAssociation date column, high chance Test Directory
            # has not been imported yet.
            errors.append(
                "ClinicalIndicationPanel table is empty, run: "
                "python manage.py seed td <td.json>"
            )

        if not TestDirectoryRelease.objects.all().exists():
            # if there's no TestDirectoryRelease, a td has not been imported yet.
            errors.append(
                "Test Directory has not yet been imported, run: "
                "python manage.py seed td <td.json>"
            )

        # block generation of genepanel.tsv if ANY data is awaiting review (pending=True)
        if ClinicalIndicationPanel.objects.filter(pending=True).exists():
            errors.append(
                "Some ClinicalIndicationPanel table values require manual review. "
                "Please resolve these through the review platform and try again"
            )

        # block generation of genepanel.tsv if ANY data is awaiting review
        # (pending=True)
        if ClinicalIndicationSuperPanel.objects.filter(pending=True).exists():
            errors.append(
                "Some ClinicalIndicationSuperPanel table values require "
                "manual review. Please resolve these through the review "
                "platform and try again"
            )

        # if any errors - raise them
        if errors:
            msg = "; ".join(errors)
            return msg
        else:
            return None

    def _generate_genepanels(self, rnas: set, output_directory: str) -> None:
        """
        Main function to generate genepanel.tsv, a file containing every clinical indications' genes
        Runs sanity checks, then calls a formatter if these pass
        Outputs the data as a csv, with columns: clinical indication, source panel, and HGNC gene ID.
        :param rnas: set of rnas
        :param output_directory: output directory
        """
        print("Creating genepanels file")

        errors = self._block_genepanels_if_db_not_ready()
        if errors:
            raise ValueError(errors)

        latest_td_release_ver = _fetch_latest_td_version()
        latest_td_instance = TestDirectoryRelease.objects.get(
            release=latest_td_release_ver
        )

        ci_panels, relevant_panels = self._get_relevant_ci_panels(latest_td_instance)
        ci_superpanels, relevant_superpanels = self._get_relevant_ci_superpanels(
            latest_td_instance
        )

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

    def get_current_transcript_clinical_status_for_g2t(
        self,
        transcript: Transcript,
        mane_select: TranscriptRelease,
        mane_plus: TranscriptRelease,
        hgmd: TranscriptRelease,
    ) -> bool | None:
        """
        Finds out whether a transcript is clinical or not, in the most-recent transcript releases.
        For each release, find entries for the transcript in the linking table.
        If any of the links are default_clinical=True, this transcript is a 'clinical transcript'
        Otherwise, this transcript is marked as 'not clinical transcript'

        :param transcript: Transcript instance
        :param mane_select: the latest MANE Select TranscriptRelease
        :param mane_plus: the latest MANE Plus Clinical TranscriptRelease
        :param hgmd: the latest HGMC TranscriptRelease
        :return: a boolean of whether the transcript is clinical or not (or None if there's no data)
        """
        mane_select_link = TranscriptReleaseTranscript.objects.filter(
            transcript_id=transcript.id, release_id=mane_select.id
        )
        mane_plus_link = TranscriptReleaseTranscript.objects.filter(
            transcript_id=transcript.id, release_id=mane_plus.id
        )
        hgmd_link = TranscriptReleaseTranscript.objects.filter(
            transcript_id=transcript.id, release_id=hgmd.id
        )

        # if there is no data for the transcript at all, return None
        poss_links = [mane_select_link, mane_plus_link, hgmd_link]
        if all(link is None for link in poss_links):
            return None
        else:
            # if any of the transcript links is set to default clinical, return True
            # note we assume 0 or 1 result only, because in the TranscriptReleaseTranscript model,
            # transcript and release are 'unique_together'
            clinical = False
            for link in poss_links:
                if link and link[0].default_clinical:
                    clinical = True
            return clinical

    def _generate_g2t(self, output_directory, ref_genome) -> None:
        """
        Main function to generate g2t.tsv
        Calls the function to get all current transcripts, then formats and writes it to file.

        :param output_directory: output directory
        :param ref_genome: ReferenceGenome instance
        """
        start = dt.datetime.now().strftime("%H:%M:%S")
        print(
            f"Creating g2t file for reference genome {ref_genome.reference_genome} at {start}"
        )

        # We need the latest releases of the transcript clinical status information
        latest_select = _get_latest_transcript_release("MANE Select", ref_genome)
        latest_plus_clinical = _get_latest_transcript_release(
            "MANE Plus Clinical", ref_genome
        )
        latest_hgmd = _get_latest_transcript_release("HGMD", ref_genome)

        if None in [latest_select, latest_plus_clinical, latest_hgmd]:
            raise ValueError(
                "One or more transcript releases (MANE or HGMD) have not yet been"
                " added to the database, so clinical status can't be assessed - aborting"
            )

        # We need all transcripts which are linked to the correct reference genome,
        # and are marked as clinical in the most up-to-date transcript sources
        ref_genome_transcripts = Transcript.objects.order_by("gene_id").filter(
            reference_genome=ref_genome
        )

        # Append per-transcript results to a list-of-dictionaries
        results = []

        for transcript in ref_genome_transcripts:
            clinical_status = self.get_current_transcript_clinical_status_for_g2t(
                transcript, latest_select, latest_plus_clinical, latest_hgmd
            )
            transcript_data = {
                "hgnc_id": transcript.gene.hgnc_id,
                "transcript": transcript.transcript,
                "clinical": clinical_status,
            }
            results.append(transcript_data)

        # Write out results
        file_time = dt.datetime.today().strftime("%Y%m%d")
        keys = results[0].keys()
        with open(
            f"{output_directory}/{file_time}_g2t.tsv", "w", newline=""
        ) as out_file:
            writer = csv.DictWriter(
                out_file, delimiter="\t", lineterminator="\n", fieldnames=keys
            )
            writer.writerows(results)

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

        # optional parser for reference genome
        parser.add_argument("--ref_genome")

        # optional parser for output directory
        parser.add_argument("--output")

    def handle(self, *args, **kwargs):
        """
        Command line handler for python manage.py generate
        e.g.
        python manage.py generate genepanels --hgnc <hgnc dump>
        python manage.py generate g2t --ref_genome <reference genome> --output <output directory>

        """
        cmd = kwargs.get("command")

        # determine if command is valid
        if not cmd or cmd not in ACCEPTABLE_COMMANDS:
            raise ValueError(
                "lack or invalid command argument."
                "Accepted commands: {}".format(ACCEPTABLE_COMMANDS)
            )

        # for either command: determine the output directory
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

        # checking args if command is genepanels:
        if cmd == "genepanels":
            # then check if hgnc dump is specified
            if not kwargs["hgnc"]:
                raise ValueError(
                    "No HGNC dump specified e.g. python manage.py generate genepanels --hgnc <path to hgnc dump>"
                )

            # validate HGNC file
            if not self._validate_hgnc(kwargs["hgnc"]):
                raise ValueError(f'HGNC file: {kwargs["hgnc"]} not valid')

            # generate genepanels.tsv
            rnas = parse_hgnc(kwargs["hgnc"])

            self._generate_genepanels(rnas, output_directory)

            print(f"Genepanel file created at {output_directory}")

        # if command is g2t, then generate g2t.tsv
        elif cmd == "g2t":
            # get the reference genome and standardise it
            if not kwargs["ref_genome"]:
                raise ValueError(
                    "No reference genome specified, e.g. python manage.py generate g2t --ref_genome GRCh37"
                )
            parsed_genome = _parse_reference_genome(kwargs.get("ref_genome"))

            try:
                # if the genome is valid, run the controller function, _generate_g2t
                genome = ReferenceGenome.objects.get(reference_genome=parsed_genome)
                self._generate_g2t(output_directory, genome)
                end = dt.datetime.now().strftime("%H:%M:%S")
                print(f"g2t file created at {output_directory} at {end}")
            except ObjectDoesNotExist:
                print("Aborting g2t: reference genome does not exist in the database")
