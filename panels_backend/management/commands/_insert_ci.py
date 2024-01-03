#!usr/bin/env python

from django.db import transaction
from packaging.version import Version

from .history import History

from panels_backend.models import (
    TestDirectoryRelease,
    TestDirectoryReleaseHistory,
    Panel,
    SuperPanel,
    ClinicalIndication,
    ClinicalIndicationPanel,
    ClinicalIndicationSuperPanel,
    ClinicalIndicationSuperPanelHistory,
    Gene,
    PanelGene,
    ClinicalIndicationPanelHistory,
    ClinicalIndicationTestMethodHistory,
    PanelGeneHistory,
    CiPanelTdRelease,
    CiPanelTdReleaseHistory,
    CiSuperpanelTdRelease,
    CiSuperpanelTdReleaseHistory,
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
    clinical_indication_panel: ClinicalIndicationPanel, user: str
) -> None:
    """
    Controller function which takes a clinical indication/panel link, and flags them for manual review.
    This is useful when a new CI is added, e.g. from test directory, and the user might want to switch to
    using that for a panel instead.

    This function is normally called when there is a new ci-panel link when seeding thus
    the old ci-panel link will be flagged to be deactivated / ignored
    while the new one will be created with pending `True`

    :param: clinical_indication_panel [ClinicalIndicationPanel] which needs to be flagged for manual
    review, usually because something has changed in the test directory
    :param: user [str] - currently a string, may one day be a User object if we get
    direct user access up and running
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
    clinical_indication_panel: ClinicalIndicationSuperPanel, user: str
) -> None:
    """
    Controller function which takes a clinical indication/superpanel link, and flags them for manual review.
    This is useful when a new CI is added, e.g. from test directory, and the user might want to switch to
    using that for a superpanel instead.

    This function is normally called when there is a new ci-superpanel link when seeding thus
    the old ci-superpanel link will be flagged to be deactivated / ignored
    while the new one will be created with pending `True`

    :param: clinical_indication_superpanel [ClinicalIndicationSuperPanel] which needs to
    be flagged for manual review, usually because something has changed in the test
    directory
    :param: user [str] - currently a string, may one day be a User object if we get
    direct user access up and running
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
    td_version: TestDirectoryRelease,
) -> ClinicalIndicationPanel:
    """
    Link a CI and panel, but set the 'pending' field to True,
    so that it shows for manual review by a user. Create a history record.
    Intended for use when you are making 'best guesses' for links based on
    previous CI-Panel links.

    In addition, link the ci-panel to the current latest TestDirectoryRelease.

    :param: panel_id [int], the ID for a Panel which needs linking to
    a relevant clinical indication
    :param: clinical_indication_id [int], the ID for a ClinicalIndication
    which needs linking to its panel
    :param: user [str], currently a string, may one day be a User object
    :param: td_version [TestDirectoryRelease], a test directory release
    """
    ci_panel_instance, created = ClinicalIndicationPanel.objects.update_or_create(
        clinical_indication_id=clinical_indication_id,
        panel_id=panel_id,
        defaults={
            "current": True,
            "pending": True,
        },
    )

    # attribute the pending Ci-Panel link to the current TestDirectoryRelease
    if ci_panel_instance and td_version:
        release_link, _ = CiPanelTdRelease.objects.get_or_create(
            ci_panel=ci_panel_instance, td_release=td_version
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
    td_version: TestDirectoryRelease,
) -> ClinicalIndicationSuperPanel:
    """
    Link a CI and superpanel, but set the 'pending' field to True,
    so that it shows for manual review by a user. Attribute the link to the specific
    version of the test directory.
    Additionally, create a history record.
    Intended for use when you are making 'best guesses' for links based on
    previous CI-SuperPanel links.

    :param: superpanel [SuperPanel], a SuperPanel which needs linking to
    a relevant clinical indication
    :param: clinical_indication [ClinicalIndication], a ClinicalIndication which
    needs linking to its panel
    :param: user [str], the user initiating the action
    :param: td_version [TestDirectoryRelease], the td release version provided by the user
    """
    (
        ci_superpanel_instance,
        created,
    ) = ClinicalIndicationSuperPanel.objects.update_or_create(
        clinical_indication=clinical_indication,
        superpanel=superpanel,
        defaults={
            "current": True,
            "pending": True,
        },
    )

    if ci_superpanel_instance and td_version:
        release_link, _ = CiSuperpanelTdRelease.objects.get_or_create(
            ci_superpanel=ci_superpanel_instance, td_release=td_version
        )

    if created:
        ClinicalIndicationSuperPanelHistory.objects.create(
            clinical_indication_superpanel=ci_superpanel_instance,
            note=History.auto_created_clinical_indication_panel(),
            user=user,
        )

    return ci_superpanel_instance


def _check_td_version_valid(
    td_version: str, latest_db_version: str, force: bool
) -> None:
    """
    Compares the current TD upload's version to the latest in the
    database. Causes exceptions to raise if the current TD upload
    is for an old or identical version of the test directory, relative to what's
    in Eris already. If everything is fine, does nothing.

    Can be overridden by passing force=True

    :param: td_version [str], the TD version parsed from the user-uploaded
    test directory file
    :param: latest_db_version [str], the latest TD version found in the
    Eris database
    :param: force [bool], an option which lets you force the upload of
    older test directory versions, even if it's already in Eris
    """
    if not latest_db_version or force:
        pass
    else:
        # if currently imported TD version is lower than latest TD version in db
        # then abort
        if Version(td_version) <= Version(latest_db_version):
            raise Exception(
                f"TD version {td_version} is less than or the same as"
                f" the version currently in the db, {latest_db_version}."
                f" Abandoning import."
            )


def _retrieve_panel_from_pa_id(pa_id: str) -> Panel | None:
    """
    Retrieve a single Panel record based on PA panel id.
    We order multiple Panel records by version and select the highest,
     to account for multiple entries.
    :param: pa_id [str]: panelapp id

    returns:
        panel_instance [Panel record] or None if a panel isn't found
    """
    panel_instance: Panel = (
        Panel.objects.filter(external_id=pa_id).order_by("-panel_version").first()
    )

    if not panel_instance:
        return None

    return panel_instance


def _retrieve_superpanel_from_pa_id(pa_id: str) -> SuperPanel | None:
    """
    Retrieve a single SuperPanel record based on PA panel id.
    We order multiple SuperPanel records by version and select the highest,
    to account for multiple entries.
    :param: pa_id [str]: panelapp id

    returns:
        panel_instance [SuperPanel record] or None if a SuperPanel isn't found
    """
    panel_instance: SuperPanel = (
        SuperPanel.objects.filter(external_id=pa_id).order_by("-panel_version").first()
    )

    if not panel_instance:
        return None

    return panel_instance


def _retrieve_unknown_metadata_records() -> tuple[None, None, None, None]:
    """
    Set unknown metadata records, as used when making panels from HGNCs, to None
    :returns:
        conf: None
        moi: None
        mop: None
        pen: None
    """
    conf = None
    moi = None
    mop = None
    pen = None

    return conf, moi, mop, pen


def _check_for_changed_pg_justification(pg_instance: PanelGene, unique_td_source: str):
    """
    For a PanelGene instance, check that the justification hasn't changed.
    If it has, update it and log it in history.
    You might run this if there's a new td import, for example.

    :param pg_instance: a PanelGene which might have changed
    :param unique_td_source: the test directory source, which can be used
    as a justification.
    """
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


def _make_panels_from_hgncs(
    ci: ClinicalIndication, td_release: TestDirectoryRelease, hgnc_list: list, user: str
) -> None:
    """
    Make Panel records from a list of HGNC ids.

    :param: ci [ClinicalIndication record], the CI record to link to the new panel
    :param: td_release [TestDirectoryRelease], the td release instance to link to the new CI-panel interaction
    :param: hgnc_list [list], list of HGNC ids which need to be made into a single panel
    :param: user [str], the current user
    """
    # get current config source and test directory date
    td_source: str = td_release.td_source
    config_source: str = td_release.config_source

    unique_td_source: str = f"{td_source} + {config_source} + {td_release.td_date}"

    conf, moi, mop, pen = _retrieve_unknown_metadata_records()

    panel_name = ",".join(sorted(hgnc_list))

    # create Panel record only when HGNC is different
    panel_instance, panel_created = Panel.objects.get_or_create(
        panel_name=panel_name,
        test_directory=True,
        defaults={
            "panel_source": unique_td_source,
            "external_id": None,
            "panel_version": None,
        },
    )

    # addition of HGNC, need to retire previous CI-Panel link
    # and make new CI-Panel link

    # link each HGNC (gene) to the created Panel record
    for hgnc_id in hgnc_list:
        gene_instance, _ = Gene.objects.get_or_create(hgnc_id=hgnc_id)

        # create PanelGene record, linking Panel to HGNC Gene, and add to History
        pg_instance, created = PanelGene.objects.get_or_create(
            panel_id=panel_instance.id,
            gene_id=gene_instance.id,
            confidence=conf,
            moi=moi,
            mop=mop,
            penetrance=pen,
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
            # a Panel-Gene record already exists - change justification
            _check_for_changed_pg_justification(pg_instance, unique_td_source)

    if panel_created:  # new panel created
        previous_ci_panels = ClinicalIndicationPanel.objects.filter(
            clinical_indication_id=ci.id,
            panel_id__test_directory=True,
            current=True,
        )  # find all previous associated ci-panel

        if previous_ci_panels:  # in the case where there are old ci-panel
            for ci_panel in previous_ci_panels:
                flag_clinical_indication_panel_for_review(
                    ci_panel, user
                )  # flag for review

                # linking old ci with new panel with pending = True
                new_clinical_indication_panel = (
                    provisionally_link_clinical_indication_to_panel(
                        panel_instance.id, ci.id, td_source, td_release
                    )
                )

                # check if there is any change in config source
                # update as appropriate
                new_clinical_indication_panel.config_source = config_source

                new_clinical_indication_panel.save()

    # a panel or ci might be newly imported (first seed), thus have no previous ci-panel link
    cpi_instance, created = ClinicalIndicationPanel.objects.get_or_create(
        clinical_indication_id=ci.id,
        panel_id=panel_instance.id,
        defaults={
            "current": True,
        },
    )
    # link it to the current test directory release
    cip_release, _ = CiPanelTdRelease.objects.get_or_create(
        ci_panel=cpi_instance, td_release=td_release
    )

    if created:
        ClinicalIndicationPanelHistory.objects.create(
            clinical_indication_panel_id=cpi_instance.id,
            note=History.clinical_indication_panel_created(),
            user=td_source,
        )


def _make_provisional_test_method_change(
    ci_instance: ClinicalIndication,
    new_test_method: str,
    user: str,
) -> None:
    """
    When a test method changes for a clinical indication,
    set the clinical indication record to `pending` = True,
    and log this in the history table.

    :param: ci_instance [ClinicalIndication record], the CI record to link to
    :param: new_test_method [str], new test method
    :param: user [str], the user initiating the action

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


def _fetch_latest_td_version() -> str | None:
    """
    Gets the highest test directory version currently in the database.
    Searches the TestDirectoryRelease table to get the highest release
    number overall.

    :returns: latest_td [str], the maximum test directory version in
    the database, or None if there isn't an entry yet
    """
    latest_tds = TestDirectoryRelease.objects.all()
    if not latest_tds:
        return None
    else:
        releases = [v.release for v in latest_tds]
        latest = max(releases, key=Version)
        return latest


def _update_ci_panel_tables_with_new_ci(
    r_code: str,
    td_version: TestDirectoryRelease,
    ci_instance: ClinicalIndication,
    user: str,
) -> None:
    """
    New clinical indication - the old CI-panel entries with the
    same R code, will be set to 'pending = True'. The new CI will be linked to
    those panels, again with 'pending = True' to make it "provisional".

    :param: r_code [str], the R code of the new clinical indication
    :param: td_version [TestDirectoryRelease], the test directory's version
    :param: ci_instance [ClinicalIndication], the new ClinicalIndication object
    in the database which may need linking to some panels
    :param: user - the current user
    """
    for clinical_indication_panel in ClinicalIndicationPanel.objects.filter(
        clinical_indication_id__r_code=r_code,
        current=True,
    ):
        # flag previous ci-panel link for review because a new ci is created
        flag_clinical_indication_panel_for_review(clinical_indication_panel, user)

        # linking new ci with old panel with pending = True
        # this might be duplicated down the line when panel is created
        # but if old panel and new panel are the same, we expect that there
        # will still be one ci-panel link instead of two being created
        previous_panel_id = clinical_indication_panel.panel_id

        provisionally_link_clinical_indication_to_panel(
            previous_panel_id, ci_instance.id, user, td_version
        )


def _update_ci_superpanel_tables_with_new_ci(
    r_code: str,
    td_version: TestDirectoryRelease,
    ci_instance: ClinicalIndication,
    user: str,
) -> None:
    """
    New clinical indication - the old CI-superpanel entries with the
    same R code, will be set to 'pending = True'. The new CI will be linked to
    those panels, again with 'pending = True' to make it "provisional".

    :param: r_code [str], the R code of the new clinical indication
    :param: td_version [TestDirectoryRelease], the test directory's version
    :param: ci_instance [ClinicalIndication], the new ClinicalIndication object
    in the database which may need linking to some superpanels
    :param: config_source [str], source metadata for the CI-superpanel link
    :param: user [str], the current user
    """
    for clinical_indication_superpanel in ClinicalIndicationSuperPanel.objects.filter(
        clinical_indication__r_code=r_code,
        current=True,
    ):
        # flag previous ci-panel link for review because a new ci is created
        flag_clinical_indication_superpanel_for_review(
            clinical_indication_superpanel, user
        )

        # linking new ci with old panel with pending = True
        # this might be duplicated down the line when panel is created
        # but if old panel and new panel are the same, we expect that there
        # will still be one ci-panel link instead of two being created
        (
            provisionally_link_clinical_indication_to_superpanel(
                clinical_indication_superpanel.superpanel, ci_instance, user, td_version
            )
        )


def _make_ci_panel_td_link(
    ci_instance: ClinicalIndication,
    panel_record: Panel,
    td_version: TestDirectoryRelease,
    user: str,
) -> tuple[ClinicalIndicationPanel, bool]:
    """
    Gets-or-creates a ClinicalIndicationPanel entry. Links to test directory release.

    :param: ci_instance [ClinicalIndication], a clinical indication which
    needs linking to a panel
    :param: panel_record [Panel], a panel which needs linking to a clinical
    indication
    :param: td_version [TestDirectoryRelease], the TD version in the current user-added source
    :param: user [str], the name of the user

    :return: a tuple containing the created or fetched ClinicalIndicationPanel
    instance, plus a bool for if it was created or not
    """
    (
        cip_instance,
        cip_created,
    ) = ClinicalIndicationPanel.objects.get_or_create(
        clinical_indication_id=ci_instance.id,
        panel_id=panel_record.id,
        defaults={"current": True},
    )

    # link the CI-Panel to the current test directory release
    cipanel_td, cipanel_td_created = CiPanelTdRelease.objects.get_or_create(
        ci_panel=cip_instance, td_release=td_version
    )

    if cip_created:
        # if CI-Panel record is created, create a history record
        ClinicalIndicationPanelHistory.objects.create(
            clinical_indication_panel_id=cip_instance.id,
            note=History.clinical_indication_panel_created(),
            user=user,
        )

    # log the fact that a td-ci_panel link was made
    if cipanel_td_created:
        CiPanelTdReleaseHistory.objects.create(
            cip_td=cipanel_td,
            note=History.td_panel_ci_autolink(
                td_version.release,
            ),
            user=user,
        )

    return cip_instance, cip_created


def _make_ci_superpanel_td_link(
    ci_instance: ClinicalIndication,
    superpanel_record: SuperPanel,
    td_version: TestDirectoryRelease,
    user: str,
) -> tuple[ClinicalIndicationSuperPanel, bool]:
    """
    Gets-or-creates a ClinicalIndicationSuperPanel entry. Link to td release.

    :param: ci_instance [ClinicalIndication], a clinical indication which
    needs linking to a panel
    :param: panel_record [Panel], a panel which needs linking to a clinical
    indication
    :param: td_version [str], the TD version in the current user-added source
    :param: user [str], the current user

    :return: a tuple containing the created or fetched ClinicalIndicationSuperPanel
    instance, plus a bool for if it was created or not
    """
    (
        cip_instance,
        cip_created,
    ) = ClinicalIndicationSuperPanel.objects.get_or_create(
        clinical_indication=ci_instance,
        superpanel=superpanel_record,
        defaults={
            "current": True,
        },
    )

    # link ci-superpanel to current test directory release
    (
        cisuperpanel_td,
        cisuperpanel_td_created,
    ) = CiSuperpanelTdRelease.objects.get_or_create(
        ci_superpanel=cip_instance, td_release=td_version
    )

    if cip_created:
        # if CI-Panel record is created, create a history record
        ClinicalIndicationSuperPanelHistory.objects.create(
            clinical_indication_superpanel=cip_instance,
            note=History.clinical_indication_superpanel_created(),
            user=user,
        ),

    # log the fact that a td-ci_panel link was made
    if cisuperpanel_td_created:
        CiSuperpanelTdReleaseHistory.objects.create(
            cip_td=cisuperpanel_td,
            note=History.td_superpanel_ci_autolink(
                cisuperpanel_td.td_release.release,
            ),
            user=user,
        )
    return cip_instance, cip_created


def _flag_panels_removed_from_test_directory(
    ci_instance: ClinicalIndication, panels: list, user: str
) -> None:
    """
    For a clinical indication, finds any pre-existing links to Panels and
    checks that each Panel is still in the test directory.
    If the Panel isn't in the test directory anymore, it sets it to Pending and logs
    information in history tables.

    :param: ci_instance, a ClinicalIndication which needs its pre-existing links
    to be found and flagged
    :param: panels, a list of relevant panels taken from the TD json or other data source
    :param: user, the current user name
    """
    ci_panels = ClinicalIndicationPanel.objects.filter(
        clinical_indication_id__r_code=ci_instance.r_code, current=True
    )

    for cip in ci_panels:
        associated_panel = Panel.objects.get(id=cip.panel_id)

        # if for the clinical indication,
        # the associated panel association is not in test directory
        # flag for review
        if associated_panel.external_id and associated_panel.external_id not in panels:
            with transaction.atomic():
                cip.pending = True
                cip.current = False
                cip.save()

                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=cip.id,
                    note=History.flag_clinical_indication_panel(
                        "ClinicalIndicationPanel does not exist in TD"
                    ),
                    user=user,
                )


def _flag_superpanels_removed_from_test_directory(
    ci_instance: ClinicalIndication, panels: list, user: str
) -> None:
    """
    For a clinical indication, finds any pre-existing links to SuperPanels and
    checks that each SuperPanel is still in the test directory.
    If a SuperPanel isn't in the test directory anymore, it sets it to Pending and logs
    information in history tables.

    :param: ci_instance, a ClinicalIndication which needs its pre-existing links
    to be found and flagged
    :param: panels, a list of relevant superpanels taken from the TD json or other
    data source
    :param: user, the current user
    """
    ci_superpanels = ClinicalIndicationSuperPanel.objects.filter(
        clinical_indication__r_code=ci_instance.r_code, current=True
    )

    for cip in ci_superpanels:
        # if the linked panel is not in test directory,
        # flag it for review
        if cip.superpanel.external_id not in panels:
            with transaction.atomic():
                cip.pending = True
                cip.current = False
                cip.save()

                ClinicalIndicationSuperPanelHistory.objects.create(
                    clinical_indication_superpanel=cip,
                    note=History.flag_clinical_indication_panel(
                        "ClinicalIndicationSuperPanel does not exist in TD"
                    ),
                    user=user,
                )


def _add_td_release_to_db(
    td_version: str, td_source: str, config_source: str, td_date: str, user: str
) -> TestDirectoryRelease:
    """
    Add a new TestDirectory to the database with a version, and make a history entry
    which will record datetime, user, and action.
    :param td_version: the string of the version of the currently-uploaded test directory
    :param td_source: the string of the source of the currently-uploaded test directory
    :param config_source: the string of the config
    :param user: the string representing the current user
    :returns: the TestDirectoryRelease
    """
    td = TestDirectoryRelease.objects.create(
        release=td_version,
        td_source=td_source,
        td_date=td_date,
        config_source=config_source,
    )

    TestDirectoryReleaseHistory.objects.create(
        td_release=td, user=user, note=History.td_added()
    )
    return td


@transaction.atomic
def insert_test_directory_data(
    json_data: dict, td_release: str, force: bool = False
) -> None:
    """This function inserts TD data into DB

    e.g. command
    python manage.py seed test_dir <input_json> --td_release <td_release_version> <Y/N>

    args:
        json_data [json dict]: data from TD
        td_release [str]: the version of the test directory file
        td_current [bool]: is this the current TD version?
    """

    print(f"Inserting test directory data into database... forced: {force}")

    # fetch td source and config source from json file
    td_source: str = json_data.get("td_source")
    assert td_source, "Missing td_source in test directory json file"
    td_date: str = json_data.get("date")
    config_source = json_data["config_source"]

    # fetch td version and check it's valid
    latest_td_version_in_db = _fetch_latest_td_version()
    _check_td_version_valid(td_release, latest_td_version_in_db, force)

    # TODO: add a useful User one day
    user = td_source

    # add test directory to the db
    td_version = _add_td_release_to_db(
        td_release, td_source, config_source, td_date, user
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
            # if a clinical indication is new to the db - check it isn't already linked to a panel
            # # under a different name. If it IS, mark the old panel link as pending,
            # and provisionally link the affected panel to this new CI
            _update_ci_panel_tables_with_new_ci(r_code, td_version, ci_instance, user)
            _update_ci_superpanel_tables_with_new_ci(
                r_code, td_version, ci_instance, user
            )

        else:
            # if this isn't a new clinical indication - check in case test method needs updating
            if ci_instance.test_method != indication["test_method"]:
                _make_provisional_test_method_change(
                    ci_instance,
                    indication["test_method"],
                    td_source,
                )

        # now that clinical indications have been made and added to the database,
        # link each CI record to the appropriate Panel records
        hgnc_list: list[str] = []

        # attaching Panels to CI
        if indication["panels"]:
            for pa_id in indication["panels"]:
                if not pa_id or not pa_id.strip():
                    continue

                # add any individual hgnc ids to a separate list
                # because they'll need to be made into a panel
                if pa_id.upper().startswith("HGNC:"):
                    hgnc_list.append(pa_id.strip().upper())
                    continue

                # for PA panel ids, retrieve latest version matching Panel and SuperPanel records
                panel_record: Panel = _retrieve_panel_from_pa_id(pa_id)
                super_panel_record: SuperPanel = _retrieve_superpanel_from_pa_id(pa_id)

                # if we import the same version of TD but with different config source:
                if panel_record:
                    cip_instance, cip_created = _make_ci_panel_td_link(
                        ci_instance, panel_record, td_version, user
                    )

                if super_panel_record:
                    cip_instance, cip_created = _make_ci_superpanel_td_link(
                        ci_instance,
                        super_panel_record,
                        td_version,
                        user,
                    )

                if not panel_record and not super_panel_record:
                    # No record exists of this panel/superpanel
                    # e.g. panel id 489 has been retired
                    print(
                        f"{indication['code']}: No Panel or SuperPanel record "
                        f"has panelapp ID {pa_id}"
                    )
                    pass

            # deal with change in clinical indication-panel/superpanel interaction
            # e.g. clinical indication R1 changed from panel 1 to panel 2
            _flag_panels_removed_from_test_directory(
                ci_instance, indication["panels"], user
            )
            _flag_superpanels_removed_from_test_directory(
                ci_instance, indication["panels"], user
            )

        if hgnc_list:
            _make_panels_from_hgncs(ci_instance, td_version, hgnc_list, user)

    _backward_deactivate(all_indication, td_source)

    print("Data insertion completed.")
    return True