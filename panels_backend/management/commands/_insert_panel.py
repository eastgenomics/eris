#!usr/bin/env python


from panels_backend.models import (
    Panel,
    SuperPanel,
    PanelSuperPanel,
    ClinicalIndicationSuperPanel,
    ClinicalIndicationPanel,
    ClinicalIndicationPanelHistory,
    Gene,
    Confidence,
    Penetrance,
    ModeOfInheritance,
    ModeOfPathogenicity,
    PanelGene,
    PanelGeneHistory,
    TestDirectoryRelease,
    CiPanelTdRelease,
    CiSuperpanelTdRelease,
)

from .utils import sortable_version
from .history import History
from ._insert_ci import (
    flag_clinical_indication_panel_for_review,
    flag_clinical_indication_superpanel_for_review,
    provisionally_link_clinical_indication_to_panel,
    provisionally_link_clinical_indication_to_superpanel,
)
from .panelapp import PanelClass, SuperPanelClass
from django.db import transaction
from packaging.version import Version


def _handle_nulls_and_blanks_from_json(json_field: str | None) -> str | None:
    """
    For an attribute extracted from the genes section
    of the PanelApp API call - check it isn't some variety of none-type data.
    Make it into None if it's none-type.
    Otherwise return a string with leading/trailing whitespace cut out.

    :param: json field (str), e.g. mode_of_inheritance, or None
    :return: the sanitised json field (str) or None
    """
    if json_field:
        json_field = json_field.strip()
        if json_field:
            return json_field
        else:
            return None
    else:
        return None


def _populate_nullable_gene_fields(
    gene: dict,
) -> tuple[ModeOfInheritance | None, ModeOfPathogenicity | None, Penetrance | None]:
    """
    Handles extracting fields which are commonly nullable and seen in gene parsing.
    Where the fields exist, make them in the db.
    Strips leading and trailing spaces for strings.

    :param: gene - a dictionary containing attributes such as moi, mop, e.t.c. Values
    might be null

    :return: moi_instance, a ModeOfInheritance instance, or None if not applicable
    :return: mop_instance, a ModeOfPathogenicity instance, or None if not applicable
    :return: penetrance, a Penetrance instance, or None if not applicable
    """
    moi_instance = None
    mop_instance = None
    penetrance_instance = None

    inheritance = _handle_nulls_and_blanks_from_json(gene.get("mode_of_inheritance"))
    if inheritance:
        moi_instance, _ = ModeOfInheritance.objects.get_or_create(
            mode_of_inheritance=inheritance
        )

    mop = _handle_nulls_and_blanks_from_json(gene.get("mode_of_pathogenicity"))
    if mop:
        mop_instance, _ = ModeOfPathogenicity.objects.get_or_create(
            mode_of_pathogenicity=mop,
        )

    penetrance = _handle_nulls_and_blanks_from_json(gene.get("penetrance"))
    if penetrance:
        penetrance_instance, _ = Penetrance.objects.get_or_create(
            penetrance=penetrance,
        )

    return moi_instance, mop_instance, penetrance_instance


def _insert_gene(
    panel: PanelClass,
    panel_instance: Panel,
    panel_created: bool,
) -> None:
    """
    Function to insert gene component of Panel into database.

    :param panel: PanelClass object
    :param panel_instance: Panel object
    :param panel_created: boolean to indicate if panel is newly created
    """
    # attaching each Gene record to Panel record
    for single_gene in panel.genes:
        gene_data: dict = single_gene.get("gene_data")

        if not gene_data:
            continue

        hgnc_id = gene_data.get("hgnc_id")
        confidence_level = single_gene.get("confidence_level")

        if not hgnc_id:
            print(
                f"For panel {str(panel.name)}, skipping gene without HGNC ID: {str(gene_data['gene_name'])}"
            )
            continue

        # there is only confidence level 0 1 2 3
        # and we only fetch confidence level 3
        try:
            if float(confidence_level) != 3.0:
                # check if panel-gene exist in db
                # flag as pending and return
                # else move on
                existing_panel_genes = PanelGene.objects.filter(
                    gene_id__hgnc_id=hgnc_id, panel_id=panel_instance.id
                )
                if existing_panel_genes.exists():
                    for panel_gene in existing_panel_genes:
                        with transaction.atomic():
                            panel_gene.active = False
                            panel_gene.pending = True
                            panel_gene.save()

                            # this is recording duplicate records as there're duplicate genes within the same panel with varying confidence level
                            # either filter out those genes or something
                            PanelGeneHistory.objects.create(
                                panel_gene_id=panel_gene.id,
                                user="PanelApp",
                                note=History.panel_gene_flagged_due_to_confidence(
                                    confidence_level
                                ),
                            )
                continue  # if panel-gene doesn't exist in db then we don't care about this gene with confidence level < 3
            else:
                pass  # if gene is confidence level 3 then we move on
        except (ValueError, TypeError):
            # the confidence_level is an alphabetical, None, or some other type that can't be converted to float
            print(
                f"For panel {str(panel.name)}, skipping gene without confidence "
                f"information: {str(gene_data['gene_name'])}"
            )
            continue

        gene_symbol = gene_data.get("gene_symbol")
        alias_symbols = gene_data.get("alias", [])

        # don't update gene symbol here. We do it when seeding hgnc dump
        gene_instance, _ = Gene.objects.get_or_create(
            hgnc_id=hgnc_id,
            defaults={
                "gene_symbol": gene_symbol,
                "alias_symbols": ",".join(sorted(alias_symbols))
                if alias_symbols
                else None,
            },
        )

        confidence_instance, _ = Confidence.objects.get_or_create(
            confidence_level=3,  # we only seed level 3 confidence
        )

        (
            moi_instance,
            mop_instance,
            penetrance_instance,
        ) = _populate_nullable_gene_fields(single_gene)

        pg_instance, pg_created = PanelGene.objects.get_or_create(
            panel_id=panel_instance.id,
            gene_id=gene_instance.id,
            defaults={
                "justification": "PanelApp",
                "confidence_id": confidence_instance.id,
                "moi_id": (moi_instance.id if moi_instance else None),
                "mop_id": (mop_instance.id if mop_instance else None),
                "penetrance_id": (
                    penetrance_instance.id if penetrance_instance else None
                ),
                "active": True,
            },
        )

        # if panel-gene record is newly created and the panel already exist in db
        # this mean the panel-gene record is newly added in PanelApp API
        # which will require our manual review
        if pg_created and not panel_created:
            pg_instance.pending = True
            pg_instance.save()

        if pg_created:
            PanelGeneHistory.objects.create(
                panel_gene_id=pg_instance.id,
                note=History.panel_gene_created(),
                user="PanelApp",
            )
        else:
            # Panel-Gene record already exist
            # meaning probably there's a new PanelApp import
            # with a different justification

            if pg_instance.justification != "PanelApp":
                PanelGeneHistory.objects.create(
                    panel_gene_id=pg_instance.id,
                    note=History.panel_gene_metadata_changed(
                        "justification",
                        pg_instance.justification,
                        "PanelApp",
                    ),
                    user="PanelApp",
                )

                pg_instance.justification = "PanelApp"
                pg_instance.save()


def _get_most_recent_td_release_for_ci_panel(
    ci_panel: ClinicalIndicationPanel,
) -> TestDirectoryRelease | None:
    """
    For a clinical indication-panel link, find the most-recent active test directory release.
    Return it, or 'none' if it fails.
    Used in cases where an inferred link is being made between a new CI and a new Panel,
    based on data which exists for earlier versions of the same R code and Panel ID.

    :param ci_panel: the ClinicalIndicationPanel for which we want the most recent td release
    :return: most recent TestDirectoryRelease, or None if no db entries
    """
    # get all td_releases
    releases = CiPanelTdRelease.objects.filter(ci_panel=ci_panel)
    if not releases:
        return None
    else:
        # get the latest release - use packaging Version to do sorting
        td_releases = [v.td_release.release for v in releases]
        latest_td = max(td_releases, key=Version)

        # return the instance for that release
        latest_td_instance = TestDirectoryRelease.objects.get(release=latest_td)
        return latest_td_instance


def _get_most_recent_td_release_for_ci_superpanel(
    ci_superpanel: ClinicalIndicationSuperPanel,
) -> TestDirectoryRelease | None:
    """
    For a clinical indication-superpanel link, find the most-recent active test directory release.
    Return it, or 'none' if it fails.
    Used in cases where an inferred link is being made between a new CI and a new SuperPanel,
    based on data which exists for earlier versions of the same R code and SuperPanel ID.
    """
    # get all td_releases
    releases = CiSuperpanelTdRelease.objects.filter(ci_superpanel=ci_superpanel)
    if not releases:
        return None
    else:
        # get the latest release - use packaging Version to do sorting
        td_releases = [v.td_release.release for v in releases]
        latest_td = max(td_releases, key=Version)

        # return the instance for that release
        latest_td_instance = TestDirectoryRelease.objects.get(release=latest_td)
        return latest_td_instance


def _disable_custom_hgnc_panels(panel: PanelClass, user: str) -> None:
    """
    Function to disable custom hgnc panels if a panel with
    similar hgnc panel name is created in PanelApp

    :param panel: PanelClass object
    :param user: user who initiated this change
    """
    genes: list[dict[str, str]] = [
        gene.get("gene_data") for gene in panel.genes if gene.get("gene_data")
    ]

    potential_hgnc_panel_name: str = "&".join(
        sorted(
            [
                gene.get("hgnc_id").strip().upper()
                for gene in genes
                if gene.get("hgnc_id")
            ]
        )
    )

    # will only have 1 hgnc panel
    hgnc_panels = Panel.objects.filter(
        panel_name=potential_hgnc_panel_name, test_directory=True
    )

    if hgnc_panels.exists():
        hgnc_panel: Panel = hgnc_panels[0]

        clinical_indication_panels = ClinicalIndicationPanel.objects.filter(
            panel_id=hgnc_panel.id,
            current=True,  # active CI-Panel links only
        )

        for cip in clinical_indication_panels:
            cip.pending = True
            cip.current = False
            cip.save()

            ClinicalIndicationPanelHistory.objects.create(
                clinical_indication_panel_id=cip.id,
                note="Panel of similar genes has been created in PanelApp",
                user=user,
            )


def _insert_panel_data_into_db(panel: PanelClass, user: str) -> Panel:
    """
    Insert data from a parsed JSON a panel record, into the database.
    Controls creation and flagging of new and old CI-Panel links,
    where the Panel version has changed.
    Controls creation of genes.

    :param: panel [PanelClass], parsed panel input from the API
    :param: user [str], the user initiating this change
    """
    panel_external_id: str = panel.id
    panel_name: str = panel.name
    panel_version: str = panel.version

    # if there's a change in the panel_name or panel_version,
    # create a new record
    panel_instance, created = Panel.objects.get_or_create(
        external_id=panel_external_id,
        panel_name=panel_name,
        panel_version=sortable_version(panel_version),
        defaults={
            "panel_source": panel.panel_source,
            "test_directory": False,
        },
    )

    # if created, the new Panel record will have a different name or version,
    # regardless of panel_source
    if created:
        # handle previous Panel(s) with similar external_id. Panel name and version aren't suited for this.
        # mark previous CI-Panel links as needing review!

        for clinical_indication_panel in ClinicalIndicationPanel.objects.filter(
            panel_id__external_id=panel_external_id,
            current=True,
        ):
            flag_clinical_indication_panel_for_review(clinical_indication_panel, user)

            clinical_indication_id = clinical_indication_panel.clinical_indication_id

            # get the most recent TestDirectoryRelease for this clinical_indication_panel,
            #  and provisionally link it
            latest_active_td_release = _get_most_recent_td_release_for_ci_panel(
                clinical_indication_panel
            )

            provisionally_link_clinical_indication_to_panel(
                panel_instance.id,
                clinical_indication_id,
                "PanelApp",
                latest_active_td_release,
            )

    # attach each Gene record to the Panel record,
    # whether it was created just now or was already in the database
    _insert_gene(panel, panel_instance, created)
    _disable_custom_hgnc_panels(panel, user)

    return panel_instance, created


def _insert_superpanel_into_db(
    superpanel: SuperPanelClass, child_panels: list[Panel], user: str
) -> None:
    """
    Insert data from a parsed SuperPanel.
    This function differs slightly from the one for Panels because:
    1. SuperPanelClass has a different structure from PanelClass.
    2. SuperPanels need linking to their child-panels.

    :param: superpanel [SuperPanelClass], parsed panel input from the API
    :param: child_panels [list[Panel]], the 'child' panels which make up
    the SuperPanel. These are already added to the db, so they're a list
    of database objects.
    :param: user [str], the user initiating this
    """
    panel_external_id: str = superpanel.id
    panel_name: str = superpanel.name
    panel_version: str = superpanel.version

    # if there's a change in the panel_name or panel_version,
    # create a new record
    superpanel, created = SuperPanel.objects.get_or_create(
        external_id=panel_external_id,
        panel_name=panel_name,
        panel_version=sortable_version(panel_version),
        defaults={
            "panel_source": superpanel.panel_source,
            "test_directory": False,
        },
    )

    if created:
        # make links between the SuperPanel and its child panels
        for child in child_panels:
            PanelSuperPanel.objects.get_or_create(panel=child, superpanel=superpanel)

        # if there are previous SuperPanel(s) with similar external_id,
        # mark previous CI-SuperPanel links as needing review
        for (
            clinical_indication_superpanel
        ) in ClinicalIndicationSuperPanel.objects.filter(
            superpanel__external_id=panel_external_id, current=True
        ):
            flag_clinical_indication_superpanel_for_review(
                clinical_indication_superpanel, user
            )

            latest_active_td_release = _get_most_recent_td_release_for_ci_superpanel(
                clinical_indication_superpanel
            )

            provisionally_link_clinical_indication_to_superpanel(
                superpanel,
                clinical_indication_superpanel.clinical_indication,
                "PanelApp",
                latest_active_td_release,
            )

    # if the superpanel hasn't just been created: the SuperPanel is either
    # brand new, or it has altered the constituent panels WITHOUT changing
    # SuperPanel name or version - this would only happen if there were
    # issues at PanelApp
    return superpanel, created


def panel_insert_controller(
    panels: list[PanelClass], superpanels: list[SuperPanelClass], user: str
):
    """
    Carries out coordination of panel creation from the 'all' command - Panels and SuperPanels are
    handled differently in the database.
    This function assumes that the most recent signed-off version is wanted for every panel
    and superpanel

    :param: panels [list[PanelClass]], a list of parsed panel input from the API
    :param: superpanels [list[SuperPanel]], a list of parsed superpanel
    input from the API
    :param: user [str], the user initiating this
    """
    # currently, we only handle Panel/SuperPanel if the panel data is from
    # PanelApp, hence adding the source manually
    for panel in panels:
        panel.panel_source = "PanelApp"  # manual addition of source
        _insert_panel_data_into_db(panel, user)

    for superpanel in superpanels:
        child_panel_instances = []
        for panel in superpanel.child_panels:
            panel.panel_source = "PanelApp"  # manual addition of source
            child_panel_instance, _ = _insert_panel_data_into_db(panel, user)
            child_panel_instances.append(child_panel_instance)
        _insert_superpanel_into_db(superpanel, child_panel_instances, user)
