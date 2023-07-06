from requests_app.models import (
    Panel,
    ClinicalIndication,
    ClinicalIndicationPanel,
    ClinicalIndicationPanelHistory,
    Gene,
    Confidence,
    Penetrance,
    ModeOfInheritance,
    ModeOfPathogenicity,
    PanelGene,
    Haploinsufficiency,
    Triplosensitivity,
    RequiredOverlap,
    VariantType,
    Region,
)

from .commands._utils import sortable_version
from django.db.models import QuerySet
from django.db import transaction


def get_panel_by_id(panel_id) -> Panel | None:
    """
    Get panel from database
    """
    try:
        results = Panel.objects.get(id=panel_id)
        return results
    except Panel.DoesNotExist:
        return None


def get_panel_by_name(panel_name) -> Panel | None:
    """
    Get panel from database by name
    """
    try:
        results = Panel.objects.filter(panel_name__iexact=panel_name)
        return results.all()
    except Panel.DoesNotExist:
        return None
    

def get_clin_indication_by_r_code(r_code) -> ClinicalIndication | None:
    """
    Get clinical indication from database by its R code
    """
    try:
        results = ClinicalIndication.objects.filter(r_code__iexact=r_code)
        return results.all()
    except ClinicalIndication.DoesNotExist:
        return None


@transaction.atomic
def get_panel_clin_indication_link(panel_id, indication_id, user) -> \
    tuple[ClinicalIndicationPanelHistory | None, str | None]:
    """
    Link a clinical indication and panel in the database, set it to 'current', and log history.
    If an entry already exists and is current, no action is taken.
    If an entry exists and is NOT current, it gets set to 'current' and the history is logged.
    Will return error message if there's more than one linking entry.
    :param: panel_id
    :param: indication_id
    :returns: the clinical_indication_panel result, but only if a change is made to it. Otherwise, returns None
    :returns: and error message if something is wrong with the database. Otherwise returns None.
    """
    try:
        results = ClinicalIndicationPanel.objects.get(
            panel_id=panel_id,
            clinical_indication_id=indication_id)

        if results.current:
            return None, None

        else:
            # make it current and add to history
            results.current = True
            results.save()

            new = ClinicalIndicationPanelHistory.objects.create(
                user=user,
                note="Existing panel/indication link set to current by user",
                clinical_indication_panel_id=results.id
            )
            new.save()
            return results, None
    
    except ClinicalIndicationPanel.DoesNotExist:
        new = clinical_indication_panel = ClinicalIndicationPanel.objects.create(
            panel_id=panel_id,
            clinical_indication_id=indication_id,
            current=True,
            config_source=user
        )
        new.save()

        # add to history
        clinical_indication_panel_id = clinical_indication_panel.id
        new = ClinicalIndicationPanelHistory.objects.create(
            user=user,
            note="Panel/indication link created and set to current by user",
            clinical_indication_panel_id=clinical_indication_panel_id
            )
        new.save()
        return clinical_indication_panel, None
    
    except ClinicalIndicationPanel.MultipleObjectsReturned:
        error = "This clinical indication and panel are linked multiple times in the linking table. Exiting."
        return None, error


@transaction.atomic
def remove_panel_clin_indication_link(panel_id, indication_id, panel_name, r_code, user) -> \
    tuple[ClinicalIndicationPanelHistory | None, str | None]:
    """
    If a panel and clinical indication are linked in the database,
    this sets 'current' to False and logs it in the history.
    """
    try:
        results = ClinicalIndicationPanel.objects.get(
            panel_id=panel_id,
            clinical_indication_id=indication_id)
        
        if results.current:
            results.current = False
            results.save()
                    
            # add to history
            clinical_indication_panel_id = results.id
            new = ClinicalIndicationPanelHistory.objects.create(
                user=user,
                note="Panel/indication link deactivated by user",
                clinical_indication_panel_id=clinical_indication_panel_id
                )
            new.save()
            return new, None

        else:
            error_msg = "The panel \"{}\" and clinical indication \"{}\" are already".format(panel_name, r_code) +\
                            " deactivated in the database. No change made."
            return None, error_msg

    except ClinicalIndicationPanel.DoesNotExist:
        error_msg = "The panel \"{}\" and clinical indication \"{}\" have never been linked \
            in the database. No change made.".format(panel_name, r_code)
        return None, error_msg
    
    except ClinicalIndicationPanel.MultipleObjectsReturned:
        error = "This clinical indication and panel are linked multiple times in the linking table. Exiting."
        return None, error
