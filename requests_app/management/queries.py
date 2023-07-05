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


@transaction.atomic
def get_panel_by_id(panel_id):
    """
    Get panel from database
    """
    try:
        results = Panel.objects.get(id=panel_id)
        return results
    except Panel.DoesNotExist:
        return None


@transaction.atomic
def get_panel_by_name(panel_name):
    """
    Get panel from database by name
    """
    try:
        results = Panel.objects.filter(panel_name__iexact=panel_name)
        return results.all()
    except Panel.DoesNotExist:
        return None
    

@transaction.atomic
def get_clin_indication_by_r_code(r_code):
    """
    Get clinical indication from database by its R code
    """
    try:
        results = ClinicalIndication.filter(r_code__iexact=r_code)
        return results.all()
    except ClinicalIndication.DoesNotExist:
        return None


@transaction.atomic
def get_panel_clin_indication_link(panel_id, indication_id):
    """
    Link a clinical indication and panel in the database, set it to 'current', and log history.
    If an entry already exists and is current, no action is taken.
    If an entry exists and is NOT current, it gets set to 'current' and the history is logged.
    """
    try:
        results = ClinicalIndicationPanel.filter(
            panel_id=panel_id,
            clinical_indication_id=indication_id)
        
        if results.current:
            return None

        else:
            # make it current and add to history
            results.current = True
            results.save()

            ClinicalIndicationPanelHistory.objects.create(
                user="test_user",
                note="Existing panel/indication link set to current by user",
                clinical_indication_panel_id=results.id
            )
            
            return results
    
    except ClinicalIndicationPanel.DoesNotExist:
        clinical_indication_panel = ClinicalIndicationPanel.objects.create(
            panel_id=panel_id,
            clinical_indication_id=indication_id,
            current=True
        )
        
        # add to history
        clinical_indication_panel_id = clinical_indication_panel.id
        ClinicalIndicationPanelHistory.objects.create(
            user="test_user",
            note="Panel/indication link created and set to current by user",
            clinical_indication_panel_id=clinical_indication_panel_id
            )
        
        return clinical_indication_panel


@transaction.atomic
def remove_panel_clin_indication_link(panel_id, indication_id, panel_name, r_code):
    """
    If a panel and clinical indication are linked in the database,
    this sets 'current' to False and logs it in the history.
    """
    try:
        results = ClinicalIndicationPanel.filter(
            panel_id=panel_id,
            clinical_indication_id=indication_id)
        
        if results.current:
            results.current = False
            results.save()
                    
            # add to history
            clinical_indication_panel_id = results.id
            ClinicalIndicationPanelHistory.objects.create(
                user="test_user",
                note="Panel/indication link deactivated by user",
                clinical_indication_panel_id=clinical_indication_panel_id
                )
            return results, None

        else:
            error_msg = "The panel \"{}\" and clinical indication \"{}\" are already  \
                            deactivated in the database. No change made.".format(panel_name, r_code)
            return None, error_msg

    except ClinicalIndicationPanel.DoesNotExist:
        error_msg = "The panel \"{}\" and clinical indication \"{}\" have never been linked \
            in the database. No change made.".format(panel_name, r_code)
        return None, error_msg