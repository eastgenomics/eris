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
)

from ._utils import sortable_version
from django.db.models import QuerySet
from django.db import transaction


# TODO: need to deal with gene removal from Panel


@transaction.atomic
def insert_data_into_db(parsed_data: dict) -> None:
    """
    Insert data from parsed JSON into database.
    """
    panel_external_id: str = parsed_data["external_id"]
    panel_name: str = parsed_data["panel_name"]
    panel_version: str = parsed_data["panel_version"]

    # created Panel record
    # if there's a change in panel_name or panel_version
    # we create a new record
    panel_instance, created = Panel.objects.get_or_create(
        external_id=panel_external_id,
        panel_name=panel_name,
        panel_version=sortable_version(panel_version),
        defaults={
            "panel_source": parsed_data["panel_source"],
            "grch37": True,
            "grch38": True,
            "test_directory": False,
        },
    )

    # if created meaning new Panel record have
    # different name or version
    # regardless of panel_source
    if created:
        # handle previous Panel with similar external_id
        # disable previous CI-Panel link

        # filter by external_id
        # because Panel name or version might be different
        previous_panel_instances: list[Panel] = Panel.objects.filter(
            external_id=panel_external_id,
            panel_version__lt=sortable_version(panel_version),
        )  # expect multiple

        # We expect PanelApp to always fetch the latest
        # version of the panel thus version control is not needed

        # do not delete previous Panel record!!

        # disable CI-Panel link if any
        # a Panel "might" have multiple CI-Panel link
        for previous_panel in previous_panel_instances:
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

    # attaching each Gene record to Panel record
    for single_gene in parsed_data["genes"]:
        gene_instance, _ = Gene.objects.update_or_create(
            hgnc_id=single_gene["hgnc_id"],
            defaults={
                "gene_symbol": single_gene["gene_symbol"],
                "alias_symbols": single_gene["alias_symbols"],
            },
        )

        confidence_instance, _ = Confidence.objects.get_or_create(
            confidence_level=single_gene["confidence_level"],
        )

        moi_instance, _ = ModeOfInheritance.objects.get_or_create(
            mode_of_inheritance=single_gene["mode_of_inheritance"],
        )

        # mop value might be None
        mop_instance, _ = ModeOfPathogenicity.objects.get_or_create(
            mode_of_pathogenicity=single_gene["mode_of_pathogenicity"],
        )

        # value for 'penetrance' might be empty
        penetrance_instance, _ = Penetrance.objects.get_or_create(
            penetrance=single_gene["penetrance"],
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
                "justification": single_gene["gene_justification"],
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

            if pg_instance.justification != single_gene["gene_justification"]:
                PanelGeneHistory.objects.create(
                    panel_gene_id=pg_instance.id,
                    note=f"Panel-Gene justification changed from {pg_instance.justification} to {single_gene['gene_justification']} by PanelApp seed.",
                )

                pg_instance.justification = single_gene["gene_justification"]
                pg_instance.save()
            else:
                pass

    # for each panel region, populate the region attribute models
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

        # attach Region record to Panel record
        Region.objects.get_or_create(
            name=single_region["name"],
            chrom=single_region["chrom"],
            start_37=single_region["start_37"],
            end_37=single_region["end_37"],
            start_38=single_region["start_38"],
            end_38=single_region["end_38"],
            type=single_region["type"],
            panel_id=panel_instance.id,
            confidence_id=confidence_instance.id,
            moi_id=moi_instance.id,
            mop_id=mop_instance.id,
            penetrance_id=penetrance_instance.id,
            haplo_id=haplo_instance.id,
            triplo_id=triplo_instance.id,
            overlap_id=overlap_instance.id,
            vartype_id=vartype_instance.id,
            justification=single_region["justification"],
        )


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
