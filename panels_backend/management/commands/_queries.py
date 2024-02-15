"""
All function used by edit.py
"""
from panels_backend.models import (
    ClinicalIndicationPanel,
    ClinicalIndicationPanelHistory,
)

from django.db.models import QuerySet
from django.db import transaction
from django.http import HttpRequest


@transaction.atomic
def activate_clinical_indication_panel(
    clinical_indication_id: int,
    panel_id: int,
    user: HttpRequest | None,
) -> None:
    """
    Fetch ci-panel and make it active.
    If it doesn't exist, create it.
    If it's already active, do nothing.

    :param clinical_indication_id: clinical indication database id
    :param panel_id: panel database id
    :param: user, either 'request.user' (if called from web) or None (if called from CLI)
    """
    try:
        # fetch ci-panel link
        cip_instance = ClinicalIndicationPanel.objects.get(
            panel_id=panel_id,
            clinical_indication_id=clinical_indication_id,
        )

        # if already current (active), do nothing
        if cip_instance.current:
            print("Clinical indication panel link already active.")
        else:
            # else make it active
            cip_instance.current = True
            cip_instance.save()

            ClinicalIndicationPanelHistory.objects.create(
                note=f"Existing ci-panel link set to active by {user}",
                clinical_indication_panel_id=cip_instance.id,
                user=user,
            )
            print(
                f"Clinical indication panel {cip_instance.id} link set to active!"
            )

    except ClinicalIndicationPanel.DoesNotExist:
        # if ci-panel link doesn't exist, create it
        cip_instance = ClinicalIndicationPanel.objects.create(
            panel_id=panel_id,
            clinical_indication_id=clinical_indication_id,
            current=True,
        )

        ClinicalIndicationPanelHistory.objects.create(
            note="Created by command line",
            clinical_indication_panel_id=cip_instance.id,
            user=user,
        )

        print(f"Clinical indication panel {cip_instance.id} link created!")


@transaction.atomic
def deactivate_clinical_indication_panel(
    clinical_indication_id: int,
    panel_id: int,
    user: HttpRequest | None = None,
) -> None:
    """
    Deactivate ci-panel link. If link doesn't exist, do nothing.

    :param clinical_indication_id: clinical indication database id
    :param panel_id: panel database id
    :param user: user who made the change
    """
    try:
        # fetch ci-panel link
        cip_instance = ClinicalIndicationPanel.objects.get(
            panel_id=panel_id, clinical_indication_id=clinical_indication_id
        )

        # if active, deactivate
        if cip_instance.current:
            cip_instance.current = False
            cip_instance.save()

            ClinicalIndicationPanelHistory.objects.create(
                note=f"Existing ci-panel link set to inactive by {user}",
                clinical_indication_panel_id=cip_instance.id,
                user=user,
            )
            print(
                f"Clinical indication panel {cip_instance.id} link set to inactive."
            )
        else:
            # ci-panel already inactive
            print("Clinical indication panel link already inactive.")

    except ClinicalIndicationPanel.DoesNotExist:
        # if ci-panel link doesn't exist, do nothing
        print("Clinical indication panel link does not exist.")
