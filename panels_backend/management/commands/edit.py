"""
python manage.py edit <--panel_id or --panel_name> <panel_id or panel_name> <--clinical_indication_id or --clinical_indication_r_code> <clinical_indication_id or clinical_indication_r_code> <activate or deactivate>
python manage.py edit --panel_id 26 --clinical_indication_id 1 activate
python manage.py edit --clinical_indication_r_code R67.1 --panel_id 26 activate
python manange.py edit --clinical_indication_id 260 panel_name "Stickler Syndrome" deactivate (case insensitive)
"""
from panels_backend.models import ClinicalIndication, Panel
from ._queries import (
    activate_clinical_indication_panel,
    deactivate_clinical_indication_panel,
)
from django.core.management.base import BaseCommand


def get_ci_from_r_code_or_id(
    ci_r_code: str | None, ci_id: str | None
) -> ClinicalIndication:
    """
    Finds the correct clinical indication, based on user-provided
    R code or ID.
    Handles logic for ambiguous R codes and raises errors if a matching
    entry doesn't exist.
    Note that this is intended for use when R code and ID are args in a
    mutually_exclusive_group, we should never get R code AND ID.

    :param: ci_r_code, R code provided by user
    (or None if not provided)
    :param: ci_id, the clinical indication's database ID provided by user
    (None if not provided)
    :return: ClinicalIndication entry matching user arg
    """
    if ci_r_code:
        clinical_indication = ClinicalIndication.objects.filter(
            r_code__iexact=ci_r_code
        )
        # foresee r-code might return multiple ci entries
        assert len(clinical_indication) < 2, (
            f"More than one clinical indication identified with r-code "
            f"{ci_r_code}. "
            "Use clinical indication database id instead to be more specific."
        )
        try:
            clinical_indication = clinical_indication[0]
        except IndexError:
            raise IndexError("No clinical indication found.")

    else:
        try:
            clinical_indication = ClinicalIndication.objects.get(id=ci_id)
        except ClinicalIndication.DoesNotExist:
            raise ClinicalIndication.DoesNotExist(
                f"The clinical indication {ci_id} was not found"
                " in the database"
            )

    return clinical_indication


def get_panel_from_id_or_name(
    panel_id: str | None, panel_name: str | None
) -> Panel:
    """
    Finds the correct panel, based on user-provided ID or name of panel.
    Handles logic for ambiguous panel names, and raises errors if a matching
    entry doesn't exist.
    Note that this is intended for use when ID and panel name are args in a
    mutually_exclusive_group, we should never get both at once.

    :param: panel_id, the panel's database ID provided by user
    (None if not provided)
    :param: panel_name, the panel's name provided by user
    (or None if not provided)
    :return: Panel entry matching user arg
    """
    if panel_id:
        try:
            panel = Panel.objects.get(id=panel_id)
        except Panel.DoesNotExist:
            raise Panel.DoesNotExist(
                f"The panel {panel_id} was not found in the database"
            )
    else:
        panel = Panel.objects.filter(panel_name__iexact=panel_name)

        # more than one panel with same name found
        assert len(panel) < 2, (
            f"More than one {panel_name} identified."
            "Use python manage.py edit [--cid/--rcode] <ci> pid <panel-id> "
            "<add/remove> instead."
        )

        # no panels with this name were found
        try:
            panel = panel[0]
        except IndexError:
            raise IndexError(f"No panel found")

    return panel


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

        # add arguments which don't change depending on whether you use panel
        # ID or name
        parser.add_argument(
            "action",
            type=str,
            choices=[
                "activate",
                "deactivate",
            ],
            help="Whether to add the clinical indication to the panel, or "
            "remove it",
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

        panel = get_panel_from_id_or_name(panel_id, panel_name)
        clinical_indication = get_ci_from_r_code_or_id(
            clinical_indication_r_code, clinical_indication_id
        )

        if action == "activate":
            # TODO: what about superpanels?
            activate_clinical_indication_panel(
                clinical_indication.id, panel.id, user=None
            )
        else:
            deactivate_clinical_indication_panel(
                clinical_indication.id,
                panel.id,
                user=None,
            )
