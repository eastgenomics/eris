"""
python manage.py edit <--panel_id or --panel_name> <panel_id or panel_name> <--clinical_indication_id or --clinical_indication_r_code> <clinical_indication_id or clinical_indication_r_code> <activate or deactivate>
python manage.py edit --panel_id 26 --clinical_indication_id 1 activate
python manage.py edit --clinical_indication_r_code R67.1 --panel_id 26 activate
python maange.py edit --clinical_indication_id 260 panel_name "Stickler Syndrome" deactivate (case insensitive)
"""
from ._queries import (
    get_panel_by_database_id,
    get_panel_by_name,
    get_clinical_indication_by_r_code,
    get_clinical_indication_by_database_id,
    activate_clinical_indication_panel,
    deactivate_clinical_indication_panel,
)
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Commands to let the user edit the database from the command line."

    def add_arguments(self, parser) -> None:
        """Define the source of the data to import."""

        panel = parser.add_mutually_exclusive_group(required=True)

        panel.add_argument(
            "--panel_id",
            type=int,
            help="panel database id",
        )

        panel.add_argument(
            "--panel_name",
            type=str,
            help="panel name",
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

        clinical_indication = parser.add_mutually_exclusive_group(
            required=True
        )

        # arg for finding clinical indication using r code
        clinical_indication.add_argument(
            "--clinical_indication_id",
            help="add or remove clinical indication-panel link using ci database id",
        )

        clinical_indication.add_argument(
            "--clinical_indication_r_code",
            help="add or remove clinical indication-panel link using ci r code",
        )

    def handle(self, **kwargs) -> None:
        """Coordinates functions to import and parse data from
        specified source, then calls inserter to insert cleaned data
        into the database."""
        print(kwargs)

        action: str = kwargs.get("action")
        panel_id = kwargs.get("panel_id")
        panel_name = kwargs.get("panel_name")
        clinical_indication_id = kwargs.get("clinical_indication_id")
        clinical_indication_r_code = kwargs.get("clinical_indication_r_code")

        assert (
            action
        ), "Please specify whether you want to add or remove the clinical indication for this panel"

        if panel_id:
            panel = get_panel_by_database_id(panel_id)

            assert panel, f"The panel {panel_id} was not found in the database"
        else:
            panel = get_panel_by_name(panel_name)

            # no panel found with the database id
            assert (
                panel
            ), f"The panel {panel_name} was not found in the database"

            # more than one panel with same name found with the database id
            assert len(panel) < 2, (
                f"More than one {panel_name} identified."
                "Use python manage.py edit [--cid/--rcode] <ci> pid <panel-id> <add/remove> instead."
            )

            panel = panel[0]

        if clinical_indication_r_code:
            clinical_indication = get_clinical_indication_by_r_code(
                clinical_indication_r_code
            )

            # foresee r-code might return multiple ci entries
            assert len(clinical_indication) < 2, (
                f"More than one clinical indication identified with r-code {clinical_indication_r_code}."
                "Use clinical indication database id instead to be more specific."
            )

            clinical_indication = clinical_indication[0]

        else:
            clinical_indication = get_clinical_indication_by_database_id(
                clinical_indication_id
            )

        assert clinical_indication, "No clinical indication found."

        if action == "activate":
            activate_clinical_indication_panel(
                clinical_indication.id, panel.id, user=None
            )
        else:
            deactivate_clinical_indication_panel(
                clinical_indication.id,
                panel.id,
                user=None,
            )
