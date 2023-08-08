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

from .utils import sortable_version
from ._insert_ci import (
    flag_clinical_indication_panel_for_review,
    provisionally_link_clinical_indication_to_panel,
)
from .panelapp import PanelClass
from django.db.models import QuerySet, Q
from django.db import transaction


def _backward_deactivate_panel_gene(panel: PanelClass, panel_instance: Panel) -> None:
    hgnc_ids: list[str] = [
        gene.get("gene_data").get("hgnc_id")
        for gene in panel.genes
        if gene.get("gene_data")
    ]

    for panel_gene in PanelGene.objects.filter(panel_id=panel_instance.id).values(
        "id", "gene_id__hgnc_id"
    ):
        if panel_gene["gene_id__hgnc_id"] not in hgnc_ids:
            pg = PanelGene.objects.get(id=panel_gene["id"])
            pg.pending = True
            pg.save()


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
            panel_id__external_id=panel_external_id
        ):
            flag_clinical_indication_panel_for_review(
                clinical_indication_panel, "PanelApp"
            )

            clinical_indication_id = clinical_indication_panel.clinical_indication_id

            provisionally_link_clinical_indication_to_panel(
                panel_instance.id, clinical_indication_id, "PanelApp"
            )

    # attach each Gene record to the new Panel record,
    # and populate region attribute models
    _insert_gene(panel, panel_instance)
    _insert_regions(panel, panel_instance)

    # backward checking if PanelGene interaction is still valid
    _backward_deactivate_panel_gene(panel, panel_instance)
