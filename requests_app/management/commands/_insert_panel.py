#!usr/bin/env python


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
    PanelGeneHistory,
    PanelRegion,
)

from ._utils import sortable_version
from .panel import PanelClass
from django.db.models import QuerySet
from django.db import transaction


# TODO: need to deal with gene removal from Panel


def single_gene_creation_controller(single_gene, gene_data: dict(), hgnc_id: int(), \
                                    panel_instance: Panel) -> None:
    """
    A controller function which makes a single gene, and also its history record.

    """
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


def single_region_creation_controller(single_region: dict(), panel_instance_id: int) \
    -> None:
    """
    Controls the creation of a single region, attached to a particular panel instance
    """
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
        start_37=single_region.get("grch37_coordinates")[0]
        if single_region.get("grch37_coordinates")
        else None,
        end_37=single_region.get("grch37_coordinates")[1]
        if single_region.get("grch37_coordinates")
        else None,
        start_38=single_region.get("grch38_coordinates")[0]
        if single_region.get("grch38_coordinates")
        else None,
        end_38=single_region.get("grch38_coordinates")[1]
        if single_region.get("grch38_coordinates")
        else None,
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
        panel_id=panel_instance_id,
        region_id=region_instance.id,
        defaults={"justification": "PanelApp"},
    )


def disable_previous_panel_instances_controller(previous_panel: Panel) -> None:
    """
    Controller function which disables links between an old panel and its clinical indications, 
    and prints a message about it.
    Note that a Panel might have multiple CI-Panel links!
    """
    previous_ci_panel_instances: QuerySet[
        ClinicalIndicationPanel
    ] = ClinicalIndicationPanel.objects.filter(
        panel_id=previous_panel.id,
        current=True,  # get those that are active
    )

    # for each previous CI-Panel instance, disable
    if previous_ci_panel_instances:
        for ci_panel_instance in previous_ci_panel_instances:
            ci_panel_instance.current = False
            ci_panel_instance.save()

            print(
                'Disabled previous CI-Panel link {} for Panel "{}"'.format(
                    ci_panel_instance.id,
                    previous_panel.panel_name,
                )
            )

    # TODO: disabling old CI-Panel link but new one need to wait till next TD import?


@transaction.atomic
def insert_data_into_db(panel: PanelClass) -> None:
    """
    Insert data from parsed JSON into database.
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

    # if created meaning new Panel record have
    # different name or version
    # regardless of panel_source
    if created:
        # handle previous Panel(s) with similar external_id. Panel name and version aren't suited for this.
        # disable previous CI-Panel links, rather than just deleting them

        previous_panel_instances: list[Panel] = Panel.objects.filter(
            external_id=panel_external_id,
            panel_version__lt=sortable_version(panel_version),
        )  

        # We expect PanelApp to always fetch the latest
        # version of the panel, thus version control is not needed
        for previous_panel in previous_panel_instances:
            disable_previous_panel_instances_controller(previous_panel)

    # attach each Gene record to the new Panel record
    for single_gene in panel.genes:
        gene_data: dict = single_gene.get("gene_data")

        if not gene_data:
            continue

        hgnc_id = gene_data.get("hgnc_id")
        confidence_level = single_gene.get("confidence_level")

        # there is only confidence level 1 2 3
        # and we only fetch confidence level 3
        if not hgnc_id or float(confidence_level) != 3.0:
            continue
    
        single_gene_creation_controller(single_gene, gene_data, hgnc_id, panel_instance)


    # for each panel region, populate the region attribute models
    for single_region in panel.regions:
        single_region_creation_controller(single_region, panel_instance.id)

        

@transaction.atomic
def insert_form_data(parsed_data: dict) -> None:
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

    # if Panel is from PanelApp
    # create new Panel (custom=True)

    # editing PanelGene interaction
    for gene in parsed_data["genes"]:
        if gene["hgnc_id"].strip() in existing_genes_in_panel:
            continue
        else:
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

    for single_region in parsed_data["regions"]:
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
