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
def check_panel_exists_by_id(panel_id):
    """
    Get panel from database
    """
    try:
        results = Panel.objects.get(id=panel_id)
        return results
    except Panel.DoesNotExist:
        return None


@transaction.atomic
def check_panel_exists_by_name(panel_name):
    """
    Get panel from database by name
    """
    try:
        results = Panel.objects.filter(panel_name__iexact=panel_name)
        return results.all()
    except Panel.DoesNotExist:
        return None


