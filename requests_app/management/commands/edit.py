"""
python manage.py edit [--rcode / --cid] <clinical indication r-code or name>  [pid/pname] <panel-id or panel-name> <activate/deactivate>
python manage.py edit --rcode R12.1 pid 1234 activate
python maange.py edit --cid 1234 pname "Stickler Syndrome" deactivate
"""
from ._queries import (
    get_panel_by_database_id,
    get_panel_by_name,
    get_clinical_indication_by_r_code,
    get_clinical_indication_by_database_id,
    activate_clinical_indication_panel,
    deactivate_clinical_indication_panel,
)
from requests_app.models import (
    ClinicalIndicationPanel,
)
from django.core.management.base import BaseCommand

POSSIBLE_COMMANDS = ["pname", "pid"]


class Command(BaseCommand):
    help = "Commands to let the user edit the database from the command line."

    # def _validate_panel_exists(self, panel) -> bool:
    # TODO: need to check the panel exists

    def add_arguments(self, parser) -> None:
        """Define the source of the data to import."""

        # python manage.py edit panel_clinical_ind <panel> <add_or_remove> <r_code>
        subparsers = parser.add_subparsers(dest="command")

        # subparser for finding panel using panel-id
        panel_id = subparsers.add_parser(
            "pid",
            help="add or remove clinical indication-panel link using panel database id",
        )
        panel_id.add_argument(
            "panel_id",
            type=int,
            help="panel name",
        )

        # subparser for finding panel using panel-name
        panel_name = subparsers.add_parser(
            "pname",
            help="add or remove clinical indication-panel link using panel name",
        )

        panel_name.add_argument(
            "panel_name",
            type=str,
            help="panel database id",
        )

        # add arguments which don't change depending on whether you use panel ID or name
        parser.add_argument(
            "action",
            type=str,
            choices=[
                "activate",
                "deactivate",
            ],
            help="Whether to add the clinical indication to the panel, or remove it",
        )

        # arg for finding clinical indication using r code
        parser.add_argument(
            "--cid",
            help="add or remove clinical indication-panel link using ci database id",
        )

        parser.add_argument(
            "--rcode",
            help="add or remove clinical indication-panel link using ci r code",
        )

    def handle(self, **kwargs) -> None:
        """Coordinates functions to import and parse data from
        specified source, then calls inserter to insert cleaned data
        into the database."""
        print(kwargs)

        command: str = kwargs.get("command")

        assert (
            command in POSSIBLE_COMMANDS
        ), "Command not available, options are: " + ", ".join(POSSIBLE_COMMANDS)

        # TODO: add user later, once we've decided on how to do that
        user = "command line"

        action: str = kwargs.get("action")

        if not action:
            raise ValueError(
                "Please specify whether you want to add or remove the clinical \
                            indication for this panel"
            )

        if command == "pid":
            panel_id: str = kwargs.get("panel_id")
            if not panel_id:
                raise ValueError("Please specify panel ID")
            panel = get_panel_by_database_id(panel_id)

            # no panel found with the database id
            if not panel:
                raise Exception(f"The panel {panel_id} was not found in the database")

        if command == "pname":
            panel_name: str = kwargs.get("panel_name")
            if not panel_name:
                raise ValueError("Please specify panel name")

            panel = get_panel_by_name(panel_name)
            # no panel found with the database id
            if not panel:
                raise Exception(f"The panel {panel_name} was not found in the database")

            # more than one panels identified with the same name
            elif len(panel) > 1:
                raise ValueError(
                    f"More than one {panel_name} identified."
                    "Use python manage.py edit [--cid/--rcode] <ci> pid <panel-id> <add/remove> instead."
                )
            # only one panel found
            else:
                panel = panel[0]

        clinical_indication_database_id = kwargs.get("cid")
        clinical_indication_r_code = kwargs.get("rcode")

        if clinical_indication_database_id and clinical_indication_r_code:
            raise ValueError(
                "Please specify either clinical indication database id or r-code, not both"
            )

        if clinical_indication_r_code:
            clinical_indication = get_clinical_indication_by_r_code(
                clinical_indication_r_code
            )

            # foresee r-code might return multiple ci entries
            if len(clinical_indication) > 1:
                raise ValueError(
                    f"More than one clinical indication identified with r-code {clinical_indication_r_code}."
                    "Use python manage.py edit --cid <clinical indication db id> [pid/pname] <panel> <add/remove> instead."
                )

            if len(clinical_indication) == 1:
                clinical_indication = clinical_indication[0]

        else:
            clinical_indication = get_clinical_indication_by_database_id(
                clinical_indication_database_id
            )

        if not clinical_indication:
            raise ValueError(f"No clinical indication found.")

        if action == "activate":
            activate_clinical_indication_panel(
                clinical_indication.id,
                panel.id,
                user,
            )
        else:
            deactivate_clinical_indication_panel(
                clinical_indication.id,
                panel.id,
                user,
            )
