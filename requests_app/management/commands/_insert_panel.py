#!usr/bin/env python


from requests_app.models import (
    Panel,
    SuperPanel,
    PanelSuperPanel,
    ClinicalIndicationSuperPanel,
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
    PanelGeneHistory,
    PanelRegion,
)

from .utils import sortable_version
from .history import History
from ._insert_ci import (
    flag_clinical_indication_panel_for_review,
    flag_clinical_indication_superpanel_for_review,
    provisionally_link_clinical_indication_to_panel,
    provisionally_link_clinical_indication_to_superpanel
)
from .panelapp import PanelClass, SuperPanelClass
from django.db import transaction


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

        # NOTE: PanelApp API returns some really stupid genes and confidence levels attached to super panel
        # e.g. panel external id 465 "Other rare neuromuscular disorders"
        # it returns 3 of the same gene FLNC with the same hgnc-id HGNC:3756
        # 2 with confidence level 3 and one with confidence level 2
        # which make no sense at all. On their website, they only showed the two with confidence level 3 (both have same hgnc id)

        # TODO: need a logic to deal with super panel showing duplicate genes but with different confidence level

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
        except TypeError:
            # the confidence_level is None or some other type that can't be converted to float
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
                "alias_symbols": ",".join(alias_symbols),
            },
        )

        confidence_instance, _ = Confidence.objects.get_or_create(
            confidence_level=3,  # we only seed level 3 confidence
        )

        moi_instance, _ = ModeOfInheritance.objects.get_or_create(
            mode_of_inheritance=single_gene.get("mode_of_inheritance"),
        )

        # mop value might be None
        mop_instance, _ = ModeOfPathogenicity.objects.get_or_create(
            mode_of_pathogenicity=single_gene.get("mode_of_pathogenicity"),
        )

        # value for 'penetrance' might be empty
        penetrance_instance, _ = Penetrance.objects.get_or_create(
            penetrance=single_gene.get("penetrance"),
        )

        pg_instance, pg_created = PanelGene.objects.get_or_create(
            panel_id=panel_instance.id,
            gene_id=gene_instance.id,
            defaults={
                "justification": "PanelApp",
                "confidence_id": confidence_instance.id,
                "moi_id": moi_instance.id,
                "mop_id": mop_instance.id,
                "penetrance_id": penetrance_instance.id,
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


def _insert_regions(panel: PanelClass, panel_instance: Panel) -> None:
    """
    Function to insert region component of Panel into database.

    :param panel: PanelClass object
    :param panel_instance: Panel object
    """

    # for each panel region, populate the region attribute models
    for single_region in panel.regions:
        confidence_instance, _ = Confidence.objects.get_or_create(
            confidence_level=single_region.get("confidence_level"),
        )

        moi_instance, _ = ModeOfInheritance.objects.get_or_create(
            mode_of_inheritance=single_region.get("mode_of_inheritance"),
        )

        vartype_instance, _ = VariantType.objects.get_or_create(
            variant_type=single_region.get("type_of_variants"),
        )

        overlap_instance, _ = RequiredOverlap.objects.get_or_create(
            required_overlap=single_region.get("required_overlap_percentage"),
        )

        mop_instance, _ = ModeOfPathogenicity.objects.get_or_create(
            mode_of_pathogenicity=single_region.get("mode_of_pathogenicity")
        )

        penetrance_instance, _ = Penetrance.objects.get_or_create(
            penetrance=single_region.get("penetrance"),
        )

        haplo_instance, _ = Haploinsufficiency.objects.get_or_create(
            haploinsufficiency=single_region.get("haploinsufficiency_score"),
        )

        triplo_instance, _ = Triplosensitivity.objects.get_or_create(
            triplosensitivity=single_region.get("triplosensitivity_score"),
        )

        # attach Region record to Panel record
        region_instance, _ = Region.objects.get_or_create(
            name=single_region.get("entity_name"),
            verbose_name=single_region.get("verbose_name"),
            chrom=single_region.get("chromosome"),
            start_37=(
                single_region.get("grch37_coordinates")[0]
                if single_region.get("grch37_coordinates")
                else None
            ),
            end_37=(
                single_region.get("grch37_coordinates")[1]
                if single_region.get("grch37_coordinates")
                else None
            ),
            start_38=(
                single_region.get("grch38_coordinates")[0]
                if single_region.get("grch38_coordinates")
                else None
            ),
            end_38=(
                single_region.get("grch38_coordinates")[1]
                if single_region.get("grch38_coordinates")
                else None
            ),
            type=single_region.get("entity_type"),
            confidence_id=confidence_instance.id,
            moi_id=moi_instance.id,
            mop_id=mop_instance.id,
            penetrance_id=penetrance_instance.id,
            haplo_id=haplo_instance.id,
            triplo_id=triplo_instance.id,
            overlap_id=overlap_instance.id,
            vartype_id=vartype_instance.id,
        )

        PanelRegion.objects.get_or_create(
            panel_id=panel_instance.id,
            region_id=region_instance.id,
            defaults={"justification": "PanelApp"},
        )
        # TODO: backward deactivation for PanelRegion, with history logging


def _insert_panel_data_into_db(panel: PanelClass, user: str) -> Panel:
    """
    Insert data from a parsed JSON a panel record, into the database.
    Controls creation and flagging of new and old CI-Panel links,
    where the Panel version has changed.
    Controls creation of genes and regions.
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
            "grch37": True,
            "grch38": True,
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
            flag_clinical_indication_panel_for_review(
                clinical_indication_panel, "PanelApp"
            )

            clinical_indication_id = clinical_indication_panel.clinical_indication_id

            provisionally_link_clinical_indication_to_panel(
                panel_instance.id, clinical_indication_id, "PanelApp"
            )

    # attach each Gene record to the Panel record,
    # whether it was created just now or was already in the database,
    # and populate region attribute models
    _insert_gene(panel, panel_instance, created)
    _insert_regions(panel, panel_instance)

    return panel_instance, created


def _insert_superpanel_into_db(superpanel: SuperPanelClass, child_panels: list[Panel], 
                               user: str) -> None:
    """
    Insert data from a parsed SuperPanel.
    This function differs slightly from the one for Panels because:
    1. SuperPanelClass has a different structure from PanelClass.
    2. SuperPanels need linking to their child-panels.
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
            "grch37": True,
            "grch38": True,
            "test_directory": False,
        },
    )
    
    if created:
        # make links between the SuperPanel and its child panels
        for child in child_panels:
            panel_link, panel_link_created = \
                PanelSuperPanel.objects.get_or_create(
                    panel=child,
                    superpanel=superpanel
                )
            
        # if there are previous SuperPanel(s) with similar external_id,
        # mark previous CI-SuperPanel links as needing review
        for clinical_indication_superpanel in ClinicalIndicationSuperPanel.objects.filter(
            superpanel__external_id=panel_external_id,
            current=True
        ):
            flag_clinical_indication_superpanel_for_review(
                clinical_indication_superpanel, "PanelApp"
            )

            provisionally_link_clinical_indication_to_superpanel(
                superpanel,
                clinical_indication_superpanel.clinical_indication,
                "PanelApp"
            )

    # if the superpanel hasn't just been created: the SuperPanel is either brand new,
    # or it has altered the constituent panels WITHOUT changing SuperPanel name or version - 
    # this would only happen if there were issues at PanelApp
    return superpanel, created


def panel_insert_controller(panels: list[PanelClass], superpanels: \
                            list[SuperPanelClass], user: str):
    """
    Carries out coordination of panel creation - Panels and SuperPanels are
    handled differently in the database.
    """
    # currently, only handle Panel/SuperPanel if the panel data is from PanelApp
    for panel in panels:
        panel_instance, _ = _insert_panel_data_into_db(panel, user)

    for superpanel in superpanels:
        child_panels = []
        for panel in superpanel.child_panels:
            child_panel_instance, _ = \
                _insert_panel_data_into_db(panel, user)
            child_panels += child_panel_instance
        _insert_superpanel_into_db(superpanel, child_panels, user)