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


def get_panel_by_id(panel_id: str) -> Panel | None:
    """
    Get panel from database
    """
    try:
        results = Panel.objects.get(id=panel_id)
        return results
    except Panel.DoesNotExist:
        return None


def get_panel_by_name(panel_name: str) -> QuerySet[Panel] | None:
    """
    Get panel from database by name
    """
    results = Panel.objects.filter(panel_name__iexact=panel_name)
    if results:
        return results.all()
    else:
        return None
    

def get_clin_indication_by_r_code(r_code: str) -> QuerySet[ClinicalIndication] | None:
    """
    Get clinical indication from database by its R code
    """
    results = ClinicalIndication.objects.filter(r_code__iexact=r_code)
    if results:
        return results.all()
    else:
        return None


def get_clin_indication_panel_links_from_clin_ind(clin_ind_id: str) -> QuerySet[ClinicalIndicationPanel] | None:
    """
    Get IDs of panels linked to a given clinical indication
    """
    results = ClinicalIndicationPanel.objects.filter(clinical_indication=clin_ind_id)
    if results:
        return results.all()
    else:
        return None


@transaction.atomic
def make_panel_clin_indication_link(panel_id: int, indication_id: int, user: str) -> \
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
        result = ClinicalIndicationPanel.objects.get(
            panel_id=panel_id,
            clinical_indication_id=indication_id)

        if result.current:
            return None, None

        else:
            # make it current and add to history
            result.current = True
            result.save()

            new = ClinicalIndicationPanelHistory.objects.create(
                user=user,
                note="Existing panel/indication link set to current by user",
                clinical_indication_panel_id=result.id
            )
            return result, None
    
    except ClinicalIndicationPanel.DoesNotExist:
        clinical_indication_panel = ClinicalIndicationPanel.objects.create(
            panel_id=panel_id,
            clinical_indication_id=indication_id,
            current=True,
            config_source=user
        )

        # add to history
        clinical_indication_panel_id = clinical_indication_panel.id
        new = ClinicalIndicationPanelHistory.objects.create(
            user=user,
            note="Panel/indication link created and set to current by user",
            clinical_indication_panel_id=clinical_indication_panel_id
            )
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
        result = ClinicalIndicationPanel.objects.get(
            panel_id=panel_id,
            clinical_indication_id=indication_id)
        
        if result.current:
            result.current = False
            result.save()
                    
            # add to history
            clinical_indication_panel_id = result.id
            new = ClinicalIndicationPanelHistory.objects.create(
                user=user,
                note="Panel/indication link deactivated by user",
                clinical_indication_panel_id=clinical_indication_panel_id
                )
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


def current_and_non_current_panel_links(clinical_indication: ClinicalIndication) \
    -> bool:
    """
    For a clinical indication, assess whether it has CURRENT links to panels or not.
    Sort these into 'current' and 'not current' lists.
    """
    current_indications = False
    ind_panel_links = get_clin_indication_panel_links_from_clin_ind(clinical_indication["id"])
    if ind_panel_links:
        for x in ind_panel_links:
            if x.current:
                current_indications = True
    return current_indications


def retrieve_active_clin_indication_by_r_code(r_code, clinical_indications) \
    -> tuple[ClinicalIndication | None, str | None]:
    """
    Controller function which takes a query in ClinicalIndications for r_code, and handles the case when you 
    have multiple results, and you only want 1 'current' indication entry.
    If there's just one result found, it will return the indication regardless of whether it's active or not.
    Generates info and error messages too.
    """
    if not clinical_indications:
        err = "The clinical indication code \"{}\" was not found in the database - please add it".format(r_code)
        return None, err
    elif len(clinical_indications) == 1:
        return clinical_indications[0], None
    else:
        # there is more than one clinical indication with the same R code 
        # (usually due to name changes) - assemble information on active and inactive links to 
        # panels
        current_indications = []
        for ind in clinical_indications.values():
            # determine whether there are any active links between indication and panel
            # print("Testing something")
            # print(type(ind))
            # print(type(ind["id"]))
            is_current = current_and_non_current_panel_links(ind)
            if is_current:
                current_indications.append(ind)

        if not current_indications:
            err = "The clinical indication \"{}\" is present more than once in the database,".format(r_code) \
            + " but none are current, so can't infer which to use -" + \
                " exiting without making changes"
            return None, err
        
        # deduplicate dict
        current_indications = [dict(t) for t in {tuple(d.items()) for d in current_indications}]

        # retrieve the case where only 1 dictionary in 'results' contains anything in 'current_indications'
        if len(current_indications) == 1:
            msg = "The clinical indication \"{}\" is present more than once in the database".format(r_code) \
                + " but only 1 has a current panel link - defaulting to the current indication"
            clin_ind = current_indications[0]
            return clin_ind, msg
        elif len(current_indications) > 1:
            err = "The clinical indication \"{}\" is present more than once in the database".format(r_code) \
                + " and multiple entries are marked current - exiting without making changes"
            return None, err
        else:
            err = "The clinical indication \"{}\" is present more than once in the database".format(r_code) \
                + " and none of the entries are marked current - exiting without making changes"
            return None, err
