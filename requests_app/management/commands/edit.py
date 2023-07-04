"""
python manage.py edit --help
"""
from requests_app.models import (
    ClinicalIndicationPanel,
    PanelGene,
    Transcript,
)

import os
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Commands to let the user edit the database from the command line."
    )


    def _validate_directory(self, path) -> bool:
        return os.path.exists(path)
    

    def add_arguments(self, parser) -> None:
        """Define the source of the data to import."""

        # python manage.py seed --debug panelapp <panel> <version>
        # python manage.py edit panel_clinical_ind clinical_indication <panel> <add_or_remove> <r_code>
        subparsers = parser.add_subparsers(dest="command")

        # Parser for panelapp command e.g. panelapp all or panelapp 1234
        panel_clinical_ind = subparsers.add_parser("panel_clinical_ind", \
                                                   help="add or remove panel information for a particular panel")
        panel_clinical_ind.add_argument(
            "panel",
            type=str,
            help="PanelApp panel, by ID",
        )

        panel_clinical_ind.add_argument(
            "add_or_remove",
            type=str,
            choices=["add", "remove"],
            help="Whether to add the clinical indication to the panel, or remove it"
        )

        panel_clinical_ind.add_argument(
            "r_code",
            type=str,
            default=None,
            help="Clinical indication, by R code",
        )

