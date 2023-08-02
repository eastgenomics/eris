#!usr/bin/env python


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
    PanelGeneHistory,
    PanelRegion,
)

from ._utils import sortable_version
from .panel import PanelClass
from django.db.models import QuerySet
from django.db import transaction


# TODO: need to deal with gene removal from Panel


def _insert_gene(panel: PanelClass, panel_instance: Panel) -> None:
    """
    Function to insert gene component of Panel into database.

    :param panel: PanelClass object
    :param panel_instance: Panel object
    """

    # attaching each Gene record to Panel record
    for single_gene in panel.genes:
        gene_data: dict = single_gene.get("gene_data")

        if not gene_data:
            continue

        hgnc_id = gene_data.get("hgnc_id")
        confidence_level = single_gene.get("confidence_level")

        # there is only confidence level 0 1 2 3
        # and we only fetch confidence level 3
        if not hgnc_id or float(confidence_level) != 3.0:
            continue

        gene_symbol = gene_data.get("gene_symbol")
        alias_symbols = gene_data.get("alias", [])

    gene_instance, _ = Gene.objects.update_or_create(
        hgnc_id=hgnc_id,
        defaults={
            "gene_symbol": gene_symbol,
            "alias_symbols": ",".join(alias_symbols),
        },
    )

    confidence_instance, _ = Confidence.objects.get_or_create(
        confidence_level=3,
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

    # create PanelGene record linking Panel to HGNC
    pg_instance, created = PanelGene.objects.get_or_create(
        panel_id=panel_instance.id,
        gene_id=gene_instance.id,
        confidence_id=confidence_instance.id,
        moi_id=moi_instance.id,
        mop_id=mop_instance.id,
        penetrance_id=penetrance_instance.id,
        defaults={
            "justification": "PanelApp",
        },
    )

    if created:
        PanelGeneHistory.objects.create(
            panel_gene_id=pg_instance.id,
            note="Created by PanelApp seed.",
        )
    else:
        # Panel-Gene record already exist
        # meaning probably there's a new PanelApp import
        # with a different justification

        if pg_instance.justification != "PanelApp":
            PanelGeneHistory.objects.create(
                panel_gene_id=pg_instance.id,
                note=f"Panel-Gene justification changed from {pg_instance.justification} to PanelApp by PanelApp seed.",
            )

            pg_instance.justification = "PanelApp"
            pg_instance.save()
        else:
            pass


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


def flag_ci_panel_instances_controller(panel: Panel, user: str) \
    -> QuerySet[ClinicalIndicationPanel] | None:
    """
    Controller function which flags ACTIVE links between a panel and its clinical indications for manual review, 
    and prints a message about it.
    This is useful when a new version of a panel comes out, and the user might want to switch to using that 
    for a clinical indication instead.
    Note that a Panel might have multiple CI-Panel links!
    """
    ci_panel_instances: QuerySet[
        ClinicalIndicationPanel
    ] = ClinicalIndicationPanel.objects.filter(
        panel_id=panel.id,
        current=True,  # get those that are active
    )

    # for each previous CI-Panel instance, flag for manual review, and add to history
    if ci_panel_instances:
        for ci_panel_instance in ci_panel_instances:
            ci_panel_instance.needs_review = True
            ci_panel_instance.save()

            ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel=ci_panel_instance.id,
                    note="Flagged for manual review - new panel version pulled from PanelApp API",
                    user=user
                )

            print(
                'Flagged previous CI-Panel link {} for Panel "{}" for manual review '.format(
                    ci_panel_instance.id, panel.panel_name) + '- a new panel version is available'
            )

        return ci_panel_instances

    else:
        return None
    # TODO: disabling old CI-Panel link but new one need to wait till next TD import?


def make_provisional_ci_panel_link(previous_panel_ci_links: QuerySet[ClinicalIndicationPanel], \
                                   panel_or_ci_instance: Panel | ClinicalIndication, \
                                    user: str, panel_or_ci: bool) -> None:
    """
    If a new version is made of a panel or a clinical indication, give it the same CI-panel links \
        as the previous, active table entry.
    However, set the 'needs_review' field to True, so that it shows for manual review by a user.
    Additionally, create a history record.
    """
    assert panel_or_ci in ["panel", "ci"]
    for prev_link in previous_panel_ci_links:
        if panel_or_ci == "panel":
            ci_panel_instance, created = ClinicalIndicationPanel.objects.get_or_create(
                clinical_indication=prev_link.clinical_indication,
                panel=panel_or_ci_instance.id,
                needs_review=True
            )
        else:
            ci_panel_instance, created = ClinicalIndicationPanel.objects.get_or_create(
                clinical_indication=panel_or_ci_instance.id,
                panel=prev_link.panel,
                needs_review=True
            )
        if created:
            ClinicalIndicationPanelHistory.objects.create(
                clinical_indication_panel=ci_panel_instance.id,
                note="Auto-created CI-panel link based on information available " +\
                    "for an earlier {}".format(panel_or_ci) + 
                    "version - needs manual review",
                user=user
            )


def single_gene_form_controller(gene, panel_id_in_db, panel_source):
    gene_instance, created = Gene.objects.get_or_create(
        hgnc_id=gene["hgnc_id"].strip(),
        defaults={
            "gene_symbol": gene["gene_symbol"],
        },
    )

    conf, _ = Confidence.objects.get_or_create(
        confidence_level=gene.get("confidence_level")
    )
    moi, _ = ModeOfInheritance.objects.get_or_create(
        mode_of_inheritance=gene.get("mode_of_inheritance")
    )
    mop, _ = ModeOfPathogenicity.objects.get_or_create(
        mode_of_pathogenicity=gene.get("mode_of_pathogenicity")
    )
    penetrance, _ = Penetrance.objects.get_or_create(
        penetrance=gene.get("penetrance")
    )

    if created:
        pg_instance = PanelGene.objects.create(
            panel_id=panel_id_in_db,
            gene_id=gene_instance.id,
            confidence_id=conf.id,
            moi_id=moi.id,
            mop_id=mop.id,
            penetrance_id=penetrance.id,
            justification=panel_source,
        )

        PanelGeneHistory.objects.create(
            panel_gene_id=pg_instance.id,
            panel_id=panel_id_in_db,
            gene_id=gene_instance.id,
        )

def single_region_form_controller(single_region, panel_id_in_db, panel_source):
    #TODO: add more explanation
    confidence_instance, _ = Confidence.objects.get_or_create(
        confidence_level=single_region["confidence_level"],
    )

    moi_instance, _ = ModeOfInheritance.objects.get_or_create(
        mode_of_inheritance=single_region["mode_of_inheritance"],
    )

    vartype_instance, _ = VariantType.objects.get_or_create(
        variant_type=single_region["variant_type"],
    )

    overlap_instance, _ = RequiredOverlap.objects.get_or_create(
        required_overlap=single_region["required_overlap"],
    )

    mop_instance, _ = ModeOfPathogenicity.objects.get_or_create(
        mode_of_pathogenicity=single_region["mode_of_pathogenicity"]
    )

    penetrance_instance, _ = Penetrance.objects.get_or_create(
        penetrance=single_region["penetrance"],
    )

    haplo_instance, _ = Haploinsufficiency.objects.get_or_create(
        haploinsufficiency=single_region["haploinsufficiency"],
    )

    triplo_instance, _ = Triplosensitivity.objects.get_or_create(
        triplosensitivity=single_region["triplosensitivity"],
    )

    # create the two genome build-specific regions
    Region.objects.get_or_create(
        name=single_region.get("name"),
        chrom=single_region.get("chrom"),
        start_37=single_region.get("start_37"),
        end_37=single_region.get("end_37"),
        start_38=single_region.get("start_38"),
        end_38=single_region.get("end_38"),
        type=single_region.get("type"),
        panel_id=panel_id_in_db,
        confidence_id=confidence_instance.id,
        moi_id=moi_instance.id,
        mop_id=mop_instance.id,
        penetrance_id=penetrance_instance.id,
        haplo_id=haplo_instance.id,
        triplo_id=triplo_instance.id,
        overlap_id=overlap_instance.id,
        vartype_id=vartype_instance.id,
        defaults={
            "justification": panel_source,
        },
    )


@transaction.atomic
def insert_data_into_db(panel: PanelClass, user: str) -> None:
    """
    Insert data from a parsed JSON of panel records, into the database.
    Controls creation and flagging of new and old CI-Panel links, 
    where the Panel version has changed.
    Controls creation of genes and regions.
    """
    panel_external_id: str = panel.id
    panel_name: str = panel.name
    panel_version: str = panel.version

    # created Panel record
    # if there's a change in panel_name or panel_version
    # we create a new record
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

    # if created = the new Panel record has a different name or version,
    # regardless of panel_source
    if created:
        # handle previous Panel(s) with similar external_id. Panel name and version aren't suited for this.
        # mark previous CI-Panel links as needing review!

        previous_panel_instances: list[Panel] = Panel.objects.filter(
            external_id=panel_external_id,
            panel_version__lt=sortable_version(panel_version),
        )  

        # if there are previous CI-Panel links, mark these as needing manual review.
        # make provisional links between the CI and our new version of the column - these will need review too.
        for previous_panel in previous_panel_instances:
            previous_panel_ci_links = flag_ci_panel_instances_controller(previous_panel, user)
            if previous_panel_ci_links:
                make_provisional_ci_panel_link(previous_panel_ci_links, panel_instance, user)

    # attach each Gene record to the new Panel record
    for single_gene in panel.genes:
        gene_data: dict = single_gene.get("gene_data")

        if not gene_data:
            continue

        hgnc_id = gene_data.get("hgnc_id")
        confidence_level = single_gene.get("confidence_level")

        # confidence levels can be 1, 2 or 3. We only fetch confidence level 3
        if not hgnc_id or float(confidence_level) != 3.0:
            continue
        single_gene_creation_controller(single_gene, gene_data, hgnc_id, panel_instance)

    # for each panel region, populate the region attribute models
    for single_region in panel.regions:
        single_region_creation_controller(single_region, panel_instance.id)

        

@transaction.atomic
def insert_form_data(parsed_data: dict) -> None:
    """
    Insert data from parsed form into db
    """
    panel_id_in_db: int = parsed_data.get("panel_id_in_database").item()
    panel_name: str = parsed_data.get("panel_name").strip()

    # check if panel-id is in the database
    if panel_id_in_db not in Panel.objects.values_list("id", flat=True):
        raise ValueError(f"Panel id {panel_id_in_db} not found in database. Aborting.")

    associated_panel: Panel = Panel.objects.get(id=panel_id_in_db)

    if associated_panel.panel_name != panel_name:
        raise ValueError(
            "Panel name in database does not match panel name in excel. Aborting."
        )

    # check if panel from db have the same name as panel in excel

    ci: str = parsed_data.get("ci").strip()

    # check if ci-code is in the database
    if ci not in ClinicalIndication.objects.values_list("r_code", flat=True):
        raise ValueError(f"CI code {ci} not found in database. Aborting.")

    panel_source: str = parsed_data.get("panel_source").strip()

    existing_genes_in_panel: list[str] = PanelGene.objects.filter(
        panel_id=panel_id_in_db
    ).values_list("gene_id__hgnc_id", flat=True)

    genes_in_excel: set[str] = [
        gene["hgnc_id"].strip() for gene in parsed_data["genes"]
    ]

    if set(existing_genes_in_panel) != set(genes_in_excel):
        print("there are gene changes in excel")

    # TODO: there can be Panel referenced to by 2 CI
    # thus just changing the PanelGene interaction is not enough
    # because this new Panel now reference more genes compared to
    # another used by another CI

    # if gene changes, create new Panel
    # new PanelGene interaction
    # disable previous current CI-Panel
    # create new CI-Panel

    # if Panel is not from PanelApp (HGNC)
    # just create new Panel

    # TODO: if Panel is from PanelApp
    # create new Panel (custom=True)

    # editing PanelGene interaction
    for gene in parsed_data["genes"]:
        if gene["hgnc_id"].strip() in existing_genes_in_panel:
            continue
        else:
            single_gene_form_controller(panel_id_in_db, panel_source)

    for single_region in parsed_data["regions"]:
        single_region_form_controller(single_region, panel_id_in_db, panel_source)
    _insert_gene(panel, panel_instance)
