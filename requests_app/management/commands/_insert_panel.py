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
)


def insert_data_into_db(parsed_data: dict) -> None:
    """
    Insert data from parsed JSON into database.
    """

    # created Panel record
    panel_instance, _ = Panel.objects.get_or_create(
        external_id=parsed_data["external_id"],
        panel_name=parsed_data["panel_name"],
        panel_source=parsed_data["panel_source"],
        panel_version=parsed_data["panel_version"],
        grch37=True,
        grch38=True,
        test_directory=False,
    )

    # create Gene record for each gene
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
        PanelGene.objects.get_or_create(
            panel_id=panel_instance.id,
            gene_id=gene_instance.id,
            confidence_id=confidence_instance.id,
            moi_id=moi_instance.id,
            mop_id=mop_instance.id,
            penetrance_id=penetrance_instance.id,
            justification=single_gene["gene_justification"],
        )

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

        # create the two genome build-specific regions
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

    return None


def insert_form_data(parsed_data: dict) -> None:
    # TODO: make new Panel record if panel doesn't exist
    # TODO: if new panel made, link CI-panel

    panel_id_in_db = parsed_data.get("panel_id_in_database")
    ci = parsed_data.get("ci")
    panel_source = parsed_data.get("panel_source")

    try:
        # check if CI code is in the database
        ci_instance = ClinicalIndication.objects.get(code=ci)
    except ClinicalIndication.DoesNotExist:
        raise ValueError(f"CI code {ci} not found in database")

    try:
        # check if CI is linked to the panel-id in the database
        ClinicalIndicationPanel.objects.get(
            clinical_indication_id=ci_instance.id,
            panel_id=panel_id_in_db,
        )
    except ClinicalIndicationPanel.DoesNotExist:
        raise ValueError(
            f"CI-panel link for {ci} and {panel_id_in_db} not found in database"
        )

    if panel_id_in_db:
        try:
            # check if panel-id is in the database
            panel_instance = Panel.objects.get(id=panel_id_in_db)
        except Panel.DoesNotExist:  # create new Panel record?
            raise ValueError(
                f"Panel ID {panel_id_in_db} not found in database"
            )
    else:
        raise ValueError("Panel ID not found")

    existing_genes_in_panel = PanelGene.objects.filter(
        panel_id=panel_id_in_db
    ).values_list("gene_id__hgnc_id", flat=True)

    for gene in parsed_data["genes"]:
        if gene["hgnc_id"] in existing_genes_in_panel:
            continue  # check and update metadata?
        else:
            gene_instance, created = Gene.objects.get_or_create(
                hgnc_id=gene["hgnc_id"],
                gene_symbol=gene["gene_symbol"],
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
                print(
                    f"New Gene record created: {gene_instance.hgnc_id} {gene_instance.gene_symbol}"
                )
                PanelGene.objects.create(
                    panel_id=panel_id_in_db,
                    gene_id=gene_instance.id,
                    confidence_id=conf.id,
                    moi_id=moi.id,
                    mop_id=mop.id,
                    penetrance_id=penetrance.id,
                    justification=panel_source,
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
            panel_id=panel_instance.id,
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
