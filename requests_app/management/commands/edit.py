"""
python manage.py edit --help
"""
from requests_app.models import (
    Panel,
    ClinicalIndicationPanel,
    PanelGene,
    Transcript,
)
from ..queries import check_panel_exists_by_id, check_panel_exists_by_name

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
        panel_id_clin_ind = subparsers.add_parser("panel_id_clin_ind", \
                                                   help="add or remove panel information for a particular pane, \
                                                    obtained using the panel's primary key")
        panel_id_clin_ind.add_argument(
            "panel_id",
            type=str,
            help="Panel by internal database ID",
        )

        panel_name_clin_ind = subparsers.add_parser("panel_name_clin_ind", \
                                                   help="add or remove panel information for a particular pane, \
                                                    obtained using the panel's name")
        panel_name_clin_ind.add_argument(
            "panel_name",
            type=str,
            help="Panel by internal database ID",
        )

        # add arguments which don't change depending on whether you use panel ID or name
        parser.add_argument(
            "add_or_remove",
            type=str,
            choices=["add", "remove"],
            help="Whether to add the clinical indication to the panel, or remove it"
        )

        parser.add_argument(
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

        # python manage.py edit panel_clinical_ind <panel_id> <add_or_remove> <clinical_indication>
        add_or_remove: str = kwargs.get("add_or_remove")
        r_code: str = kwargs.get("r_code")

        if not add_or_remove:
            raise ValueError("Please specify whether you want to add or remove the clinical \
                            indication for this panel")
        if not r_code:
            raise ValueError("Please specify R code")
        
        if command == "panel_id_clin_ind":
            panel_id: str = kwargs.get("panel_id")
            if not panel_id:
                raise ValueError("Please specify panel ID")
            panel = check_panel_exists_by_id(panel_id)
            if not panel:
                print("The panel ID {} was not found in the database".format(panel_id))
                exit(1)
                
        elif command == "panel_name_clin_ind":
            panel_name: str = kwargs.get("panel_name")
            if not panel_name:
                raise ValueError("Please specify panel name")
            panel = check_panel_exists_by_name(panel_name)
            # TODO: complain if panel has more than 1 result
            if not panel:
                print("The panel name \"{}\" was not found in the database".format(panel_name))
                exit(1)
            if len(panel) > 1:
                print("The panel name \"{}\" is present twice - please try command \"panel_id_clin_ind\" \
                      with ID".format(panel_name))
                exit(1)
            else:
                panel = panel[0]

        # TODO: validate clinical_indication ('r_code') exists - prompt for it to be added to the database otherwise
    
        #TODO: fetch the clinical indication - complain if absent
        #TODO: check the panel and clinical indication aren't already linked - message if yes
        

