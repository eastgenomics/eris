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


