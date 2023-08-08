#!usr/bin/env python

# TODO: deal with PA ids which aren't in the db (looking at you 489) - Panel has been retired!

import os

from django.db import transaction
from django.db.models import QuerySet

from .utils import sortable_version, normalize_version

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
    ClinicalIndicationPanelHistory,
    ClinicalIndicationTestMethodHistory,
    PanelGeneHistory,
)


def _flag_current_links_for_ci(prev_ci: str, user: str) \
    -> QuerySet[ClinicalIndicationPanel] | None:
    """
    Controller function which takes a clinical indication r code, and flags ACTIVE links between the CI 
    and its panels for manual review.
    This is useful when a new CI is added, e.g. from test directory, and the user might want to switch to 
    using that for a panel instead.
    Note that a ClinicalIndication might have multiple CI-Panel links!
    """
    ci_panel_instances: QuerySet[
        ClinicalIndicationPanel
    ] = ClinicalIndicationPanel.objects.filter(
        clinical_indication=prev_ci,
        current=True,  # get those that are active
    )

    # for each previous CI-Panel instance, flag for manual review, and add to history
    if ci_panel_instances:
        for ci_panel_instance in ci_panel_instances:
            ci_panel_instance.needs_review = True
            ci_panel_instance.save()

            ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel=ci_panel_instance,
                    note="Flagged for manual review - new clinical indication provided",
                    user=user
                )

            print(
                'Flagged for manual review - a new clinical indication is available'
            )

        return ci_panel_instances

    else:
        return None


def _provisionally_link_new_ci_version_to_panel(previous_panel_ci_links: QuerySet[ClinicalIndicationPanel], \
                                   new_ci: ClinicalIndication, \
                                    user: str) -> None:
    """
    If a new version is made of a clinical indication, give it the same CI-panel links \
        as the previous, active table entry.
    However, set the 'needs_review' field to True, so that it shows for manual review by a user.
    Additionally, create a history record.
    """
    for prev_link in previous_panel_ci_links:
        ci_panel_instance, created = ClinicalIndicationPanel.objects.get_or_create(
            clinical_indication=new_ci,
            panel=prev_link.panel,
            current=True,
            needs_review=True        )

        if created:
            ClinicalIndicationPanelHistory.objects.create(
                clinical_indication_panel=ci_panel_instance,
                note="Auto-created CI-panel link based on information available " +\
                    "for an earlier CI version - needs manual review",
                user=user
            )
        
        #TODO: what to do if the link already existed? Is this a possible behaviour?
        #TODO: do we want to search for a 'current=False' version first, and possibly
        # TODO: switch it to True?


def _get_td_version(filename: str) -> str | None:
    """
    Get TD version from filename.
    convert "rare-and-inherited-disease-national-genomic-test-directory-v4.xlsx" into "4"

    :param: filename [str]: filename of TD json file

    returns:
        td_version [str]: TD version e.g. 4
    """

    # grab only filename without the extension
    td_filename, _ = os.path.splitext(filename)

    try:
        return td_filename.split("-")[-1].lstrip("v").strip()
    except IndexError:
        print(f"TD version not found in filename {filename}")
        return None


def _retrieve_panel_from_pa_id(ci_code: str, pa_id: str) -> Panel | None:
    """
    Retrieve a single Panel record based on PA panel id.

    :param: ci_code [str]: clinical indication code
    :param: pa_id [str]: panelapp id

    returns:
        panel_instance [Panel record]
    """

    # retrieve Panel records directly created from PA panels with that external_id
    # there might be multiple Panel records with the same external_id
    # but different versions / ids thus we order by version

    panel_instance: Panel = (
        Panel.objects.filter(external_id=pa_id).order_by("-panel_version").first()
    )

    if not panel_instance:
        print(f"{ci_code}: No Panel record has panelapp ID {pa_id}")
        return None

    return panel_instance


def _retrieve_unknown_metadata_records():
    """
    Retrieve additional metadata records for PanelGene records

    returns:
        conf [Confidence record]
        moi [ModeOfInheritance record]
        mop [ModeOfPathogenicity record]
        pen [Penetrance record]
    """

    conf, _ = Confidence.objects.get_or_create(confidence_level=None)

    moi, _ = ModeOfInheritance.objects.get_or_create(mode_of_inheritance=None)

    mop, _ = ModeOfPathogenicity.objects.get_or_create(mode_of_pathogenicity=None)

    pen, _ = Penetrance.objects.get_or_create(penetrance=None)

    return conf, moi, mop, pen


def _make_panels_from_hgncs(
    json_data: dict,
    ci: ClinicalIndication,
    hgnc_list: list,
) -> None:
    """
    Make Panel records from a list of HGNC ids.

    args:
        current [bool]: is this the current TD version
        source [str]: source of data (variable from TD.json)
        ci [ClinicalIndication record]: the CI record to link to
        hgnc_list [list]: list of HGNC ids

    """

    # get current td version
    td_source: str = json_data["td_source"]
    td_version: str = _get_td_version(td_source)

    # TODO: what if TD version is lower

    config_source: str = json_data["config_source"]
    td_date: str = json_data["date"]

    unique_td_source: str = f"{td_source} + {config_source} + {td_date}"

    conf, moi, mop, pen = _retrieve_unknown_metadata_records()

    # create Panel record only when HGNC difference
    panel_instance, panel_created = Panel.objects.get_or_create(
        panel_name=",".join(hgnc_list),
        test_directory=True,
        defaults={
            "panel_source": unique_td_source,
            "grch37": True,
            "grch38": True,
            "external_id": None,
            "panel_version": None,
        },
    )

    # addition of HGNC, need to retire previous CI-Panel link
    # and make new CI-Panel link

    # link each HGNC (gene) to the created Panel record
    for hgnc_id in hgnc_list:
        gene_instance, _ = Gene.objects.get_or_create(hgnc_id=hgnc_id)

        # create PanelGene record linking Panel to HGNC
        pg_instance, created = PanelGene.objects.get_or_create(
            panel_id=panel_instance.id,
            gene_id=gene_instance.id,
            confidence_id=conf.id,
            moi_id=moi.id,
            mop_id=mop.id,
            penetrance_id=pen.id,
            defaults={
                "justification": unique_td_source,
            },
        )

        if created:
            PanelGeneHistory.objects.create(
                panel_gene_id=pg_instance.id,
                note=f"PanelGene record created from {unique_td_source}",
            )
        else:
            # Panel-Gene record already exists
            # change justification because new TD import

            if pg_instance.justification != unique_td_source:
                PanelGeneHistory.objects.create(
                    panel_gene_id=pg_instance.id,
                    note=f"Panel-Gene justification changed from {pg_instance.justification} to {unique_td_source} by TD seed.",
                )

                pg_instance.justification = unique_td_source
                pg_instance.save()

    # if new Panel record created, check if there is old CI-Panel record
    # if so, deactivate it
    if panel_created:
        # check if previous CI-Panel record exists
        # only fetch CI-Panel records where Panel is created from Test Directory
        # only fetch CI-Panel records which are current
        previous_ci_panels: QuerySet[
            ClinicalIndicationPanel
        ] = ClinicalIndicationPanel.objects.filter(
            clinical_indication_id=ci.id,
            panel_id__test_directory=True,
            current=True,
        ).order_by(
            "-td_version"
        )
        # TODO: there is still some logic error here
        # deactivate all previous CI-Panel records
        # where Panel is created from Test Directory
        # ignore those from PanelApp
        for ci_panel in previous_ci_panels:
            # existing CI-Panel td version is higher than current imported td version
            if sortable_version(ci_panel.td_version) > sortable_version(td_version):
                return

            ci_panel.current = False
            ci_panel.save()

            ClinicalIndicationPanelHistory.objects.create(
                clinical_indication_panel_id=ci_panel.id,
                note="Deactivated by td source",
                user=td_source,
            )

    # make new CI-Panel link
    cpi_instance, created = ClinicalIndicationPanel.objects.get_or_create(
        clinical_indication_id=ci.id,
        panel_id=panel_instance.id,
        current=True,
        defaults={
            "td_version": sortable_version(td_version),
            "config_source": config_source,
        },
    )

    if created:
        ClinicalIndicationPanelHistory.objects.create(
            clinical_indication_panel_id=cpi_instance.id,
            note="Created by td source",
            user=td_source,
        )
    else:
        # check if there is any change in td version or config source
        # update as appropriate
        with transaction.atomic():
            if sortable_version(td_version) >= sortable_version(
                cpi_instance.td_version
            ):
                # take a note of the change
                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=cpi_instance.id,
                    note=f"TD version modified by td source: {normalize_version(cpi_instance.td_version)} -> {td_version}",
                    user=td_source,
                )
                cpi_instance.td_version = sortable_version(td_version)

            if cpi_instance.config_source != json_data["config_source"]:
                # take a note of the change
                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=cpi_instance.id,
                    note=f"Config source modified by td source: {cpi_instance.config_source} -> {config_source}",
                    user=td_source,
                )
                cpi_instance.config_source = config_source

            cpi_instance.save()


def make_provisional_test_method_change(ci_instance: ClinicalIndication, new_test_method: str, \
                                        user: str) -> None:
    """
    When a test method changes for a clinical indication, 
    set the clinical indication record to 'needs_review'=True,
    and log this in the history table.
    """
    ClinicalIndicationTestMethodHistory.objects.create(
        clinical_indication_id=ci_instance.id,
        note=f"Needs review of 'test method' - modified by td source: {ci_instance.test_method} -> \
            {new_test_method}",
        user=user,
    )

    ci_instance.needs_review = True
    ci_instance.test_method = new_test_method

    ci_instance.save()


@transaction.atomic
def insert_test_directory_data(json_data: dict, user:str, force: bool = False) -> None:
    """This function insert TD data into DB

    e.g. command
    python manage.py seed test_dir <input_json> <Y/N>

    args:
        json_data [json dict]: data from TD
        td_current [bool]: is this the current TD version
    """

    print("Inserting test directory data into database...")

    # fetch td source from json file
    td_source: str = json_data.get("td_source")
    assert td_source, "Missing td_source in test directory json file"

    # fetch TD version from filename
    td_version: str = _get_td_version(td_source)
    assert td_version, f"Cannot parse TD version {td_version}"

    # fetch latest TD version in database
    latest_td_version_in_db: ClinicalIndicationPanel = (
        ClinicalIndicationPanel.objects.order_by("-td_version").first()
    )

    if not latest_td_version_in_db or force:
        pass
    else:
        # if currently imported TD version is lower than latest TD version in db
        # then abort
        if sortable_version(td_version) <= sortable_version(
            latest_td_version_in_db.td_version
        ):
            print(f"TD version {td_version} already in database. Abdandoning import.")
            return

    for indication in json_data["indications"]:
        r_code: str = indication["code"].strip()

        ci_instance, created = ClinicalIndication.objects.get_or_create(
            r_code=r_code,
            name=indication["name"],
            defaults={
                "test_method": indication["test_method"],
            },
        )

        if created:
            # New clinical indication - the old CI-panel entries with the same R code, 
            # will be set to 'needs_review=True'. The new CI will be linked to those panels, 
            # again with 'needs_review=True' to make it provisional.
            previous_cis = list[ClinicalIndication] = ClinicalIndication.objects.filter(
                r_code=r_code, current=True).exclude(pk=ci_instance.id)

            for previous_ci in previous_cis:
                previous_panel_ci_links = \
                    _flag_current_links_for_ci(previous_ci, user)
                if previous_panel_ci_links:
                    _provisionally_link_new_ci_version_to_panel(previous_panel_ci_links, \
                                                                ci_instance, user)

        else:
            # Check for change in test method
            if ci_instance.test_method != indication["test_method"]:
                make_provisional_test_method_change(ci_instance, indication["test_method"])

        # link each CI record to the appropriate Panel records
        hgnc_list: list[str] = []

        # attaching Panels to CI
        if indication["panels"]:
            for pa_id in indication["panels"]:
                if not pa_id or not pa_id.strip():
                    continue

                # add any individual hgnc ids to a separate list
                if pa_id.upper().startswith("HGNC:"):
                    hgnc_list.append(pa_id.strip().upper())
                    continue

                # for PA panel ids, retrieve latest version matching Panel records
                panel_record: Panel = _retrieve_panel_from_pa_id(
                    indication["code"],
                    pa_id,
                )

                # if we import the same version of TD but with different config source
                if panel_record:
                    (
                        cip_instance,
                        created,
                    ) = ClinicalIndicationPanel.objects.get_or_create(
                        clinical_indication_id=ci_instance.id,
                        panel_id=panel_record.id,
                        current=True,
                        defaults={
                            "td_version": sortable_version(td_version),
                            "config_source": json_data["config_source"],
                        },
                    )

                    if created:
                        # if CI-Panel record is created, create a history record
                        ClinicalIndicationPanelHistory.objects.create(
                            clinical_indication_panel_id=cip_instance.id,
                            note="Created by td source",
                            user=td_source,
                        )
                    else:
                        # if CI-Panel already exist and the link is the same
                        # just update the config source and td version (if different)
                        with transaction.atomic():
                            if sortable_version(td_version) >= sortable_version(
                                cip_instance.td_version
                            ):
                                # take a note of the change
                                ClinicalIndicationPanelHistory.objects.create(
                                    clinical_indication_panel_id=cip_instance.id,
                                    note=f"TD version modified by td source: {normalize_version(cip_instance.td_version)} -> {td_version}",
                                    user=td_source,
                                )
                                cip_instance.td_version = sortable_version(td_version)

                            if cip_instance.config_source != json_data["config_source"]:
                                # take a note of the change
                                ClinicalIndicationPanelHistory.objects.create(
                                    clinical_indication_panel_id=cip_instance.id,
                                    note=f"Config source modified by td source: {cip_instance.config_source} -> {json_data['config_source']}",
                                    user=td_source,
                                )
                                cip_instance.config_source = json_data["config_source"]

                            cip_instance.save()

                else:
                    # No panel record exist
                    # e.g. panel id 489 has been retired
                    print(
                        f"{indication['code']}: No Panel record has panelapp ID {pa_id}"
                    )
                    pass

        if hgnc_list:
            _make_panels_from_hgncs(json_data, ci_instance, hgnc_list)

        # deal with deactivating CI-Panel records which are no longer in TD
        # TODO: above

    print("Data insertion completed.")
