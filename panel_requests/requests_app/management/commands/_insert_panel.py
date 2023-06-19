#!usr/bin/env python


from panel_requests.requests_app.models import (
    Panel,
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


# @transaction.atomic
# def update_ci_panel_links(r_code, link_source, req_date, new_panels):
#     """Update records for associations between a CI and its panels when
#     a new panel is imported.

#     args:
#         r_code [str]
#         link_source [str]: e.g. a test directory or request form
#         date [str]: date of source
#         new_panels [list]: new Panel records (i.e. for both genome builds)
#     """

#     print("Updating database links between panels and clinical indication...")

#     date = dt.strptime(req_date, "%Y%m%d")

#     # get the CI record (there should be exactly 1 for each R code)

#     ci_records = ClinicalIndication.objects.filter(code=r_code)

#     assert (
#         len(ci_records) == 1
#     ), f"Error: {r_code} has {len(ci_records)} CI records (should be 1)"

#     # get current links to Panel records (should be either 0 or 2)

#     ci_panels = ClinicalIndicationPanel.objects.filter(
#         clinical_indication=ci_records[0].id, current=True
#     )

#     assert len(ci_panels) in [
#         0,
#         2,
#     ], f"Error: {r_code} has {len(ci_panels)} panel links (should be 0 or 2)"

#     # change existing ci-panel links so they're no longer current

#     if ci_panels:
#         for link in ci_panels:
#             link.current = False
#             link.save()

#             # update link's usage record (should be exactly 1) with end date

#             usages = ClinicalIndicationPanelUsage.objects.filter(
#                 clinical_indication_panel=link.id
#             )

#             assert len(usages) == 1, (
#                 f"Error: An {r_code}-panel link has {len(usages)}"
#                 " usage records (should be 1)"
#             )

#             usages[0].end_date = date
#             usages[0].save()

#     # create new ci-panel link, usage and source records

#     for panel in new_panels:
#         source, _ = CiPanelAssociationSource.objects.get_or_create(
#             source=link_source, date=date
#         )

#         ci_panel, _ = ClinicalIndicationPanel.objects.get_or_create(
#             source=source, clinical_indication=ci_records[0], panel=panel, current=True
#         )

#         _, _ = ClinicalIndicationPanelUsage.objects.get_or_create(
#             clinical_indication_panel=ci_panel, start_date=date, end_date=None
#         )

#     print("Database updated.")
