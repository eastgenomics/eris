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

    #def _validate_panel_exists(self, panel) -> bool:
        #TODO: need to check the panel exists


    def add_arguments(self, parser) -> None:
        """Define the source of the data to import."""

        # python manage.py edit panel_clinical_ind <panel> <add_or_remove> <r_code>
        subparsers = parser.add_subparsers(dest="command")

        # Parser for command
        panel_clinical_ind = subparsers.add_parser("panel_clinical_ind", \
                                                   help="add or remove panel information for a particular panel")
        panel_clinical_ind.add_argument(
            "panel_id",
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

    def handle(self, *args, **kwargs) -> None:
        """Coordinates functions to import and parse data from
        specified source, then calls inserter to insert cleaned data
        into the database."""
        print(kwargs)

        test_mode: bool = kwargs.get("debug", False)
        command: str = kwargs.get("command")

        assert command, "Command error"

        # TODO: validate panel_id exists
        # TODO: validate r_code exists - prompt for it to be added to the database otherwise

        # python manage.py edit panel_clinical_ind <panel_id> <add_or_remove> <clinical_indication>
        if command == "panel_clinical_ind":
            panel_id: str = kwargs.get("panel_id")
            add_or_remove: str = kwargs.get("add_or_remove")
            r_code: str = kwargs.get("r_code")

            if not panel_id:
                raise ValueError("Please specify panel ID")
            
            if not add_or_remove:
                raise ValueError("Please specify whether you want to add or remove the clinical \
                                indication for this panel")
            
            if not r_code:
                raise ValueError("Please specify R code")
        
