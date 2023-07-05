from requests_app.models import (
    Panel,
    ClinicalIndication,
    ClinicalIndicationPanel,
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
    Look up whether a clinical indication and panel ID have ever been linked
    in the database
    """
    try:
        results = ClinicalIndicationPanel.filter(panel_id=panel_id, clinical_indication_id=indication_id)
        return results.all()
    except ClinicalIndicationPanel.DoesNotExist:
        return None
    
