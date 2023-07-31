"""
All function used by edit.py
"""
from requests_app.models import (
    Panel,
    ClinicalIndication,
    ClinicalIndicationPanel,
    ClinicalIndicationPanelHistory,
)

from django.db.models import QuerySet
from django.db import transaction


def get_panel_by_database_id(panel_id: str) -> Panel | None:
    """
    Get panel from database
    """
    try:
        return Panel.objects.get(id=panel_id)
    except Panel.DoesNotExist:
        return None


def get_panel_by_name(panel_name: str) -> QuerySet[Panel] | None:
    """
    Get panel from database by name
    """

    try:
        return Panel.objects.filter(panel_name__iexact=panel_name)
    except Panel.DoesNotExist:
        return None


def get_clinical_indication_by_r_code(
    r_code: str,
) -> QuerySet[ClinicalIndication]:
    """
    Get clinical indication by its R code
    """
    return ClinicalIndication.objects.filter(r_code__iexact=r_code)


def get_clinical_indication_by_database_id(id: str) -> ClinicalIndication | None:
    """
    Get clinical indication by databse id
    """
    try:
        return ClinicalIndication.objects.get(id=id)
    except ClinicalIndication.DoesNotExist:
        return None


@transaction.atomic
def activate_clinical_indication_panel(
    clinical_indication_id: int,
    panel_id: int,
    user: str,
) -> None:
    """
    Fetch ci-panel and make it active. If it doesn't exist, create it.
    """
    try:
        cip_instance = ClinicalIndicationPanel.objects.get(
            panel_id=panel_id,
            clinical_indication_id=clinical_indication_id,
        )

        if cip_instance.current:
            print("Clinical indication panel link already active.")
        else:
            cip_instance.current = True
            cip_instance.save()

            ClinicalIndicationPanelHistory.objects.create(
                user=user,
                note=f"Existing ci-panel link set to active by {user}",
                clinical_indication_panel_id=cip_instance.id,
            )
            print(f"Clinical indication panel {cip_instance.id} link set to active!")

    except ClinicalIndicationPanel.DoesNotExist:
        cip_instance = ClinicalIndicationPanel.objects.create(
            panel_id=panel_id,
            clinical_indication_id=clinical_indication_id,
            current=True,
        )

        ClinicalIndicationPanelHistory.objects.create(
            user=user,
            note="Created by command line",
            clinical_indication_panel_id=cip_instance.id,
        )

        print(f"Clinical indication panel {cip_instance.id} link created!")


@transaction.atomic
def deactivate_clinical_indication_panel(
    clinical_indication_id: int,
    panel_id: int,
    user: str,
) -> None:
    """
    Deactivate ci-panel link. If link doesn't exist, do nothing.
    """
    try:
        cip_instance = ClinicalIndicationPanel.objects.get(
            panel_id=panel_id, clinical_indication_id=clinical_indication_id
        )

        if cip_instance.current:
            cip_instance.current = False
            cip_instance.save()

            ClinicalIndicationPanelHistory.objects.create(
                user=user,
                note=f"Existing ci-panel link set to inactive by {user}",
                clinical_indication_panel_id=cip_instance.id,
            )
            print(f"Clinical indication panel {cip_instance.id} link set to inactive.")
        else:
            print("Clinical indication panel link already inactive.")

    except ClinicalIndicationPanel.DoesNotExist:
        print("Clinical indication panel link does not exist.")
