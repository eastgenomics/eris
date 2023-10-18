#!usr/bin/env python

# TODO: deal with PA ids which aren't in the db (looking at you 489) - Panel has been retired!

import os

from django.db import transaction

from .utils import sortable_version, normalize_version
from .history import History

from requests_app.models import (
    Panel,
    SuperPanel,
    ClinicalIndication,
    ClinicalIndicationPanel,
    ClinicalIndicationSuperPanel,
    ClinicalIndicationSuperPanelHistory,
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


def _backward_deactivate(indications: list[dict], user: str) -> None:
    """
    This function flag any clinical indication that doesn't exist in TestDirectory

    :params: indications [list]: list of clinical indication from TD
    :params: user [str]: user who is importing the TD
    """
    r_codes = set([indication["code"] for indication in indications])

    for clinical_indication in ClinicalIndication.objects.all():
        if clinical_indication.r_code not in r_codes:
            for cip in ClinicalIndicationPanel.objects.filter(
                clinical_indication_id=clinical_indication.id
            ):
                cip.current = False  # deactivate ci-panel link
                cip.pending = True
                cip.save()

                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=cip.id,
                    note=History.flag_clinical_indication_panel(
                        "clinical indication not found in latest TD"
                    ),
                    user=user,
                )


@transaction.atomic
def flag_clinical_indication_panel_for_review(
    clinical_indication_panel: ClinicalIndicationPanel, 
    user: str
) -> None:
    """
    Controller function which takes a clinical indication/panel link, and flags them for manual review.
    This is useful when a new CI is added, e.g. from test directory, and the user might want to switch to
    using that for a panel instead.

    This function is normally called when there is a new ci-panel link when seeding thus
    the old ci-panel link will be flagged to be deactivated / ignored
    while the new one will be created with pending `True`
    """

    clinical_indication_panel.pending = True
    clinical_indication_panel.current = False
    # this function mainly deal with old ci-panel link so changing `current` here to False make sense
    clinical_indication_panel.save()

    ClinicalIndicationPanelHistory.objects.create(
        clinical_indication_panel_id=clinical_indication_panel.id,
        note=History.flag_clinical_indication_panel("new clinical indication provided"),
        user=user,
    )


def flag_clinical_indication_superpanel_for_review(
    clinical_indication_panel: ClinicalIndicationSuperPanel, 
    user: str
) -> None:
    """
    Controller function which takes a clinical indication/superpanel link, and flags them for manual review.
    This is useful when a new CI is added, e.g. from test directory, and the user might want to switch to
    using that for a superpanel instead.

    This function is normally called when there is a new ci-superpanel link when seeding thus
    the old ci-superpanel link will be flagged to be deactivated / ignored
    while the new one will be created with pending `True`
    """

    clinical_indication_panel.pending = True
    clinical_indication_panel.current = False
    # this function mainly deal with old ci-panel link so changing `current` here to False make sense
    clinical_indication_panel.save()

    ClinicalIndicationSuperPanelHistory.objects.create(
        clinical_indication_superpanel=clinical_indication_panel,
        note=History.flag_clinical_indication_panel("new clinical indication provided"),
        user=user,
    )


def provisionally_link_clinical_indication_to_panel(
    panel_id: int,
    clinical_indication_id: int,
    user: str,
) -> ClinicalIndicationPanel:
    """
    Link a CI and panel, but set the 'pending' field to True,
    so that it shows for manual review by a user.
    Additionally, create a history record.
    Intended for use when you are making 'best guesses' for links based on
    previous CI-Panel links.
    """
    ci_panel_instance, created = ClinicalIndicationPanel.objects.update_or_create(
        clinical_indication_id=clinical_indication_id,
        panel_id=panel_id,
        defaults={
            "current": True,
            "pending": True,
        },
    )

    if created:
        ClinicalIndicationPanelHistory.objects.create(
            clinical_indication_panel_id=ci_panel_instance.id,
            note=History.auto_created_clinical_indication_panel(),
            user=user,
        )

    return ci_panel_instance


def provisionally_link_clinical_indication_to_superpanel(
    superpanel: SuperPanel,
    clinical_indication: ClinicalIndication,
    user: str,
) -> ClinicalIndicationSuperPanel:
    """
    Link a CI and superpanel, but set the 'pending' field to True,
    so that it shows for manual review by a user.
    Additionally, create a history record.
    Intended for use when you are making 'best guesses' for links based on
    previous CI-SuperPanel links.
    """
    ci_superpanel_instance, created = ClinicalIndicationSuperPanel.objects.update_or_create(
        clinical_indication=clinical_indication,
        superpanel=superpanel,
        defaults={
            "current": True,
            "pending": True,
        },
    )

    if created:
        ClinicalIndicationSuperPanelHistory.objects.create(
            clinical_indication_superpanel=ci_superpanel_instance,
            note=History.auto_created_clinical_indication_panel(),
            user=user,
        )

    return ci_superpanel_instance


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

def _retrieve_superpanel_from_pa_id(ci_code: str, pa_id: str) -> SuperPanel | None:
    """
    Retrieve a single SuperPanel record based on PA panel id.

    :param: ci_code [str]: clinical indication code
    :param: pa_id [str]: panelapp id

    returns:
        panel_instance [SuperPanel record]
    """

    # retrieve SuperPanel records directly created from PA panels with that external_id
    # there might be multiple SuperPanel records with the same external_id
    # but different versions / ids thus we order by version

    panel_instance: SuperPanel = (
        SuperPanel.objects.filter(external_id=pa_id).order_by("-panel_version").first()
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

    config_source: str = json_data["config_source"]
    td_date: str = json_data["date"]

    unique_td_source: str = f"{td_source} + {config_source} + {td_date}"

    conf, moi, mop, pen = _retrieve_unknown_metadata_records()

    # basically the max length of panel_name of Panel mode is 255
    # if the length of panel_name is more than 255, truncate it to 245 and add TRUNCATED (9 chars) which will be 254 chars in total

    panel_name = ",".join(sorted(hgnc_list))
    formatted_panel_name = (
        panel_name[:245] + "TRUNCATED" if len(panel_name) > 255 else panel_name
    )

    # create Panel record only when HGNC difference
    panel_instance, panel_created = Panel.objects.get_or_create(
        panel_name=formatted_panel_name,
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
            active=True,  # this should be True because it's linking HGNC panel to HGNC
            defaults={
                "justification": unique_td_source,
            },
        )

        if created:
            PanelGeneHistory.objects.create(
                panel_gene_id=pg_instance.id,
                note=History.panel_gene_created(),
                user=unique_td_source,
            )
        else:
            # Panel-Gene record already exists
            # change justification because new TD import

            if pg_instance.justification != unique_td_source:
                PanelGeneHistory.objects.create(
                    panel_gene_id=pg_instance.id,
                    note=History.panel_gene_metadata_changed(
                        "justification",
                        pg_instance.justification,
                        unique_td_source,
                    ),
                    user=unique_td_source,
                )

                pg_instance.justification = unique_td_source
                pg_instance.save()

    if panel_created:  # new panel created
        previous_ci_panels = ClinicalIndicationPanel.objects.filter(
            clinical_indication_id=ci.id,
            panel_id__test_directory=True,
            current=True,
        ).order_by(
            "-td_version"
        )  # find all previous associated ci-panel

        if previous_ci_panels:  # in the case where there are old ci-panel
            for ci_panel in previous_ci_panels:
                flag_clinical_indication_panel_for_review(
                    ci_panel, td_source
                )  # flag for review

                # linking old ci with new panel with pending = True
                new_clinical_indication_panel = (
                    provisionally_link_clinical_indication_to_panel(
                        panel_instance.id, ci.id, td_source
                    )
                )

                # check if there is any change in td version or config source
                # update as appropriate
                new_clinical_indication_panel.td_version = sortable_version(td_version)
                new_clinical_indication_panel.config_source = config_source

                new_clinical_indication_panel.save()

    # a panel or ci might be newly imported (first seed), thus have no previous ci-panel link
    cpi_instance, created = ClinicalIndicationPanel.objects.get_or_create(
        clinical_indication_id=ci.id,
        panel_id=panel_instance.id,
        defaults={
            "current": True,
            "td_version": sortable_version(td_version),
            "config_source": config_source,
        },
    )

    if created:
        ClinicalIndicationPanelHistory.objects.create(
            clinical_indication_panel_id=cpi_instance.id,
            note=History.clinical_indication_panel_created(),
            user=td_source,
        )
    else:
        # panel already exist
        with transaction.atomic():
            if sortable_version(td_version) != cpi_instance.td_version:
                # take a note of the change
                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=cpi_instance.id,
                    note=History.clinical_indication_panel_metadata_changed(
                        "td_version",
                        normalize_version(cpi_instance.td_version),
                        td_version,
                    ),
                    user=td_source,
                )
                cpi_instance.td_version = sortable_version(td_version)
            if cpi_instance.config_source != json_data["config_source"]:
                # take a note of the change
                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=cpi_instance.id,
                    note=History.clinical_indication_panel_metadata_changed(
                        "config_source",
                        cpi_instance.config_source,
                        config_source,
                    ),
                    user=td_source,
                )
                cpi_instance.config_source = config_source
            cpi_instance.save()


def _make_provisional_test_method_change(
    ci_instance: ClinicalIndication,
    new_test_method: str,
    user: str,
) -> None:
    """
    When a test method changes for a clinical indication,
    set the clinical indication record to `pending` = True,
    and log this in the history table.

    args:
        ci_instance [ClinicalIndication record]: the CI record to link to
        new_test_method [str]: new test method
        user [str]: # TODO: will need some thought on this

    return: None
    """

    with transaction.atomic():
        # record the change in history table first before making the change
        ClinicalIndicationTestMethodHistory.objects.create(
            clinical_indication_id=ci_instance.id,
            note=History.clinical_indication_metadata_changed(
                "test_method",
                ci_instance.test_method,
                new_test_method,
            ),
            user=user,
        )

        ci_instance.pending = True
        ci_instance.test_method = new_test_method

        ci_instance.save()

def _fetch_latest_td_version() -> str:
    """
    Gets the highest test directory version currently in the database.
    Searches the CI-Panel and CI-SuperPanel tables to get the highest 
    number overall.
    Returns the max number.
    """
    latest_td_version_in_panels: ClinicalIndicationPanel = (
        ClinicalIndicationPanel.objects.filter(td_version__isnull=False)
        .order_by("-td_version")
        .first()
    )

    latest_td_version_in_superpanels: ClinicalIndicationSuperPanel = (
        ClinicalIndicationSuperPanel.objects.filter(td_version__isnull=False)
        .order_by("-td_version")
        .first()
    )

    latest_td_version_in_db = max([latest_td_version_in_panels,
                             latest_td_version_in_superpanels])
    
    return latest_td_version_in_db


def _update_ci_panel_tables_with_new_ci(r_code, td_source, td_version, ci_instance,
                               config_source):
    """
    New clinical indication - the old CI-panel and CI-superpanel entries with the
    same R code, will be set to 'pending = True'. The new CI will be linked to 
    those panels, again with 'pending = True' to make it "provisional".
    """
    for clinical_indication_panel in ClinicalIndicationPanel.objects.filter(
        clinical_indication_id__r_code=r_code,
        current=True,
    ):
        # flag previous ci-panel link for review because a new ci is created
        flag_clinical_indication_panel_for_review(
            clinical_indication_panel, td_source
        )

        # linking new ci with old panel with pending = True
        # this might be duplicated down the line when panel is created
        # but if old panel and new panel are the same, we expect that there
        # will still be one ci-panel link instead of two being created
        previous_panel_id = clinical_indication_panel.panel_id

        new_clinical_indication_panel = (
            provisionally_link_clinical_indication_to_panel(
                previous_panel_id,
                ci_instance.id,
                td_source,
            )
        )

        # fill in new clinical indication - panel link metadata
        new_clinical_indication_panel.td_version = sortable_version(td_version)
        new_clinical_indication_panel.config_source = config_source
        new_clinical_indication_panel.save()

def _update_ci_superpanel_tables_with_new_ci(r_code, td_source, td_version, ci_instance,
                               config_source):
    """
    New clinical indication - the old CI-superpanel entries with the
    same R code, will be set to 'pending = True'. The new CI will be linked to 
    those panels, again with 'pending = True' to make it "provisional".
    """
    for clinical_indication_superpanel in ClinicalIndicationSuperPanel.objects.filter(
        clinical_indication_id__r_code=r_code,
        current=True,
    ):
        # flag previous ci-panel link for review because a new ci is created
        flag_clinical_indication_superpanel_for_review(
            clinical_indication_superpanel, td_source
        )

        # linking new ci with old panel with pending = True
        # this might be duplicated down the line when panel is created
        # but if old panel and new panel are the same, we expect that there
        # will still be one ci-panel link instead of two being created
        new_clinical_indication_superpanel = (
            provisionally_link_clinical_indication_to_superpanel(
                clinical_indication_superpanel,
                ci_instance,
                td_source,
            )
        )

        # fill in new clinical indication - panel link metadata
        new_clinical_indication_superpanel.td_version = sortable_version(td_version)
        new_clinical_indication_superpanel.config_source = config_source
        new_clinical_indication_superpanel.save()

def _update_ci_panel_links(cip_instance, td_version, td_source,
                           config_source):
    """
    If CI-Panel already exists and the link is the same,
    just update the config source and td version (if different)
    """
    with transaction.atomic():
        if sortable_version(td_version) >= sortable_version(
            cip_instance.td_version
        ):
            # take a note of the change
            ClinicalIndicationPanelHistory.objects.create(
                clinical_indication_panel_id=cip_instance.id,
                note=History.clinical_indication_panel_metadata_changed(
                    "td_version",
                    normalize_version(cip_instance.td_version),
                    td_version,
                ),
                user=td_source,
            )
            cip_instance.td_version = sortable_version(td_version)

        if cip_instance.config_source != config_source:
            # take a note of the change
            ClinicalIndicationPanelHistory.objects.create(
                clinical_indication_panel_id=cip_instance.id,
                note=History.clinical_indication_panel_metadata_changed(
                    "config_source",
                    cip_instance.config_source,
                    config_source
                ),
                user=td_source,
            )
            cip_instance.config_source = config_source

        cip_instance.save()

def _update_ci_superpanel_links(cip_instance, td_version, td_source,
                           config_source):
    """
    If CI-SuperPanel already exists and the link is the same,
    just update the config source and td version (if different)
    """
    with transaction.atomic():
        if sortable_version(td_version) >= sortable_version(
            cip_instance.td_version
        ):
            # take a note of the change
            ClinicalIndicationSuperPanelHistory.objects.create(
                clinical_indication_panel_id=cip_instance.id,
                note=History.clinical_indication_panel_metadata_changed(
                    "td_version",
                    normalize_version(cip_instance.td_version),
                    td_version,
                ),
                user=td_source,
            )
            cip_instance.td_version = sortable_version(td_version)

        if cip_instance.config_source != config_source:
            # take a note of the change
            ClinicalIndicationSuperPanelHistory.objects.create(
                clinical_indication_panel_id=cip_instance.id,
                note=History.clinical_indication_panel_metadata_changed(
                    "config_source",
                    cip_instance.config_source,
                    config_source
                ),
                user=td_source,
            )
            cip_instance.config_source = config_source

        cip_instance.save()

def _attempt_ci_panel_creation(ci_instance, panel_record, td_version,
                               td_source, config_source):
    """
    Gets-or-creates a ClinicalIndicationPanel entry.
    If the entry is new, it will log history too.
    """
    (
        cip_instance,
        cip_created,
    ) = ClinicalIndicationPanel.objects.get_or_create(
        clinical_indication_id=ci_instance.id,
        panel_id=panel_record.id,
        defaults={
            "current": True,
            "td_version": sortable_version(td_version),
            "config_source": config_source,
        },
    )

    if cip_created:
        # if CI-Panel record is created, create a history record
        ClinicalIndicationPanelHistory.objects.create(
            clinical_indication_panel_id=cip_instance.id,
            note=History.clinical_indication_panel_created(),
            user=td_source,
        )

    return cip_instance, cip_created

def _attempt_ci_superpanel_creation(ci_instance, superpanel_record, td_version,
                               td_source, config_source):
    """
    Gets-or-creates a ClinicalIndicationSuperPanel entry.
    If the entry is new, it will log history too.
    """
    (
        cip_instance,
        cip_created,
    ) = ClinicalIndicationSuperPanel.objects.get_or_create(
        clinical_indication=ci_instance,
        panel=superpanel_record,
        defaults={
            "current": True,
            "td_version": sortable_version(td_version),
            "config_source": config_source,
        },
    )

    if cip_created:
        # if CI-Panel record is created, create a history record
        ClinicalIndicationSuperPanelHistory.objects.create(
            clinical_indication_panel=cip_instance,
            note=History.clinical_indication_panel_created(),
            user=td_source,
        )

    return cip_instance, cip_created

@transaction.atomic
def insert_test_directory_data(json_data: dict, force: bool = False) -> None:
    """This function insert TD data into DB

    e.g. command
    python manage.py seed test_dir <input_json> <Y/N>

    args:
        json_data [json dict]: data from TD
        td_current [bool]: is this the current TD version
    """

    print(f"Inserting test directory data into database... forced: {force}")

    # fetch td source from json file
    td_source: str = json_data.get("td_source")
    assert td_source, "Missing td_source in test directory json file"

    # fetch TD version from filename
    td_version: str = _get_td_version(td_source)
    assert td_version, f"Cannot parse TD version {td_version}"

    # fetch latest TD version in database
    latest_td_version_in_db = _fetch_latest_td_version()

    if not latest_td_version_in_db or force:
        pass
    else:
        # if currently imported TD version is lower than latest TD version in db
        # then abort
        if sortable_version(td_version) <= sortable_version(
            latest_td_version_in_db.td_version
        ):
            raise Exception(
                f"TD version {td_version} lower than one in db {normalize_version(
                    latest_td_version_in_db.td_version)}. Abdandoning import."
            )

    all_indication: list[dict] = json_data["indications"]

    for indication in all_indication:
        r_code: str = indication["code"].strip()

        ci_instance, ci_created = ClinicalIndication.objects.get_or_create(
            r_code=r_code,
            name=indication["name"],
            defaults={
                "test_method": indication["test_method"],
            },
        )

        if ci_created:
            _update_ci_panel_tables_with_new_ci(r_code, td_source, td_version, ci_instance,
                               json_data["config_source"])
            _update_ci_superpanel_tables_with_new_ci(r_code, td_source, td_version, ci_instance,
                               json_data["config_source"])
            
        else:
            # Check for change in test method
            if ci_instance.test_method != indication["test_method"]:
                _make_provisional_test_method_change(
                    ci_instance,
                    indication["test_method"],
                    td_source,
                )

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

                super_panel_record: SuperPanel = _retrieve_superpanel_from_pa_id(
                    indication["code"],
                    pa_id
                )

                # if we import the same version of TD but with different config source:
                if panel_record:
                    cip_instance, cip_created = \
                        _attempt_ci_panel_creation(ci_instance, panel_record, td_version,
                               td_source, json_data["config_source"])
                    if not cip_created:
                        _update_ci_panel_links(cip_instance, td_version, td_source,
                           json_data["config_source"])

                if super_panel_record:
                    cip_instance, cip_created = \
                        _attempt_ci_superpanel_creation(ci_instance, super_panel_record,
                                                        td_version, td_source,
                                                        json_data["config_source"])
                    
                    if not cip_created:
                        _update_ci_superpanel_links(cip_instance, td_version, td_source,
                           json_data["config_source"])
                        
                if not panel_record or super_panel_record:
                    # No panel record exist
                    # e.g. panel id 489 has been retired
                    print(
                        f"{indication['code']}: No Panel or SuperPanel record 
                        has panelapp ID {pa_id}"
                    )
                    pass

            #TODO: ensure SuperPanels added too

            # deal with change in clinical indication-panel interaction
            # e.g. clinical indication R1 changed from panel 1 to panel 2
            for cip in ClinicalIndicationPanel.objects.filter(
                clinical_indication_id__r_code=ci_instance.r_code,
                current=True,
            ):
                # grab associated panel
                associated_panel = Panel.objects.get(id=cip.panel_id)

                # if for the clinical indication
                # the associated panel association is not in test directory
                # flag for review
                if (
                    associated_panel.external_id
                    and associated_panel.external_id not in indication["panels"]
                ):
                    with transaction.atomic():
                        cip.pending = True
                        cip.current = False
                        cip.save()

                        ClinicalIndicationPanelHistory.objects.create(
                            clinical_indication_panel_id=cip.id,
                            note=History.flag_clinical_indication_panel(
                                "ClinicalIndicationPanel does not exist in TD"
                            ),
                            user=td_source,
                        )

        if hgnc_list:
            _make_panels_from_hgncs(json_data, ci_instance, hgnc_list)

    _backward_deactivate(all_indication, td_source)

    print("Data insertion completed.")
    return True
