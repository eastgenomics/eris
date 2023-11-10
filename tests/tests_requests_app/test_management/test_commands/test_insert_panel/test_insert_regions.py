from django.test import TestCase
from django.db.models import QuerySet
from django_mock_queries.query import MockSet, MockModel

from requests_app.models import (
    Panel,
    Chromosome,
    Confidence,
    ModeOfInheritance,
    Penetrance,
    ModeOfPathogenicity,
    Region,
    PanelRegion,
    VariantType,
    Haploinsufficiency,
    RequiredOverlap,
    Triplosensitivity,
    ReferenceGenome,
)

from requests_app.management.commands._insert_panel import _insert_regions

from requests_app.management.commands.panelapp import PanelClass
from .test_insert_gene import len_check_wrapper, value_check_wrapper


## _insert_regions
class TestInsertRegions_NewRegion(TestCase):
    def setUp(self) -> None:
        """
        Scenario: a new panel has been made in the database
        No regions have been linked to it yet, at this point in the code
        """
        self.first_panel = Panel.objects.create(
            external_id="162",
            panel_name="Severe microcephaly",
            panel_source="PanelApp",
            panel_version="4.31",
        )

    def test_new_panel_linked_to_acceptable_region(self):
        errors = []

        # make one of the test inputs for the function
        test_panel = PanelClass(
            id="162",
            name="Severe microcephaly",
            version="4.31",
            panel_source="PanelApp",
            genes=[],
            regions=[
                {
                    "gene_data": None,
                    "entity_type": "region",
                    "entity_name": "ISCA-37390-Loss",
                    "verbose_name": "5p15 terminal (Cri du chat syndrome) region Loss",
                    "confidence_level": "3",
                    "penetrance": None,
                    "mode_of_pathogenicity": None,
                    "haploinsufficiency_score": "3",
                    "triplosensitivity_score": "",
                    "required_overlap_percentage": 60,
                    "type_of_variants": "cnv_loss",
                    "mode_of_inheritance": "MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown",
                    "chromosome": "5",
                    "grch37_coordinates": None,
                    "grch38_coordinates": [37695, 11347150],
                },
                {
                    "gene_data": None,
                    "entity_type": "region",
                    "entity_name": "ISCA-37406-Loss",
                    "verbose_name": "16p13.3 region (includes CREBBP) Loss",
                    "confidence_level": "3",
                    "penetrance": None,
                    "mode_of_pathogenicity": None,
                    "haploinsufficiency_score": "3",
                    "triplosensitivity_score": "",
                    "required_overlap_percentage": 60,
                    "type_of_variants": "cnv_loss",
                    "mode_of_inheritance": "MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown",
                    "chromosome": "16",
                    "grch37_coordinates": None,
                    "grch38_coordinates": [3725055, 3880120],
                },
            ],
        )

        _insert_regions(test_panel, self.first_panel)

        # check that both regions have been added to the database
        regions = Region.objects.all()
        errors += len_check_wrapper(regions, "regions", 2)
        errors += value_check_wrapper(regions[0].name, "region name", "ISCA-37390-Loss")
        errors += value_check_wrapper(regions[1].name, "region name", "ISCA-37406-Loss")

        # check that both regions are linked to the correct panel
        panel_regions = PanelRegion.objects.all()
        errors += len_check_wrapper(panel_regions, "panel regions", 2)
        first_panel_regions = panel_regions[0]
        second_panel_regions = panel_regions[1]

        errors += value_check_wrapper(
            first_panel_regions.panel, "first panel-region panel", self.first_panel
        )
        errors += value_check_wrapper(
            first_panel_regions.region, "first panel-region region", regions[0]
        )
        errors += value_check_wrapper(
            second_panel_regions.panel, "second panel-region panel", self.first_panel
        )
        errors += value_check_wrapper(
            second_panel_regions.region, "second panel-region region", regions[1]
        )

        errors = "".join(errors)
        assert not errors, errors

    def test_new_panel_linked_to_multiple_regions(self):
        """
        CASE: Multiple regions are added, and each region has coordinates for GRCh37 AND
        GRCh38.
        EXPECT: 4 Regions objects are created - because there are 2 regions, each with 2 ref genomes
        """
        errors = []

        # make one of the test inputs for the function
        test_panel = PanelClass(
            id="162",
            name="Severe microcephaly",
            version="4.31",
            panel_source="PanelApp",
            genes=[],
            regions=[
                {
                    "gene_data": None,
                    "entity_type": "region",
                    "entity_name": "ISCA-37390-Loss",
                    "verbose_name": "5p15 terminal (Cri du chat syndrome) region Loss",
                    "confidence_level": "3",
                    "penetrance": None,
                    "mode_of_pathogenicity": None,
                    "haploinsufficiency_score": "3",
                    "triplosensitivity_score": "",
                    "required_overlap_percentage": 60,
                    "type_of_variants": "cnv_loss",
                    "mode_of_inheritance": "MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown",
                    "chromosome": "5",
                    "grch37_coordinates": [100, 200],
                    "grch38_coordinates": [37695, 11347150],
                },
                {
                    "gene_data": None,
                    "entity_type": "region",
                    "entity_name": "ISCA-37406-Loss",
                    "verbose_name": "16p13.3 region (includes CREBBP) Loss",
                    "confidence_level": "3",
                    "penetrance": None,
                    "mode_of_pathogenicity": None,
                    "haploinsufficiency_score": "3",
                    "triplosensitivity_score": "",
                    "required_overlap_percentage": 60,
                    "type_of_variants": "cnv_loss",
                    "mode_of_inheritance": "MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown",
                    "chromosome": "16",
                    "grch37_coordinates": [400, 500],
                    "grch38_coordinates": [3725055, 3880120],
                },
            ],
        )

        _insert_regions(test_panel, self.first_panel)

        # check that both regions have been added to the database
        # they will each have 2 db entries, due to different coordinates
        regions = Region.objects.all()
        errors += len_check_wrapper(regions, "regions", 4)
        errors += value_check_wrapper(regions[0].name, "region name", "ISCA-37390-Loss")
        errors += value_check_wrapper(regions[1].name, "region name", "ISCA-37390-Loss")
        errors += value_check_wrapper(regions[2].name, "region name", "ISCA-37406-Loss")
        errors += value_check_wrapper(regions[3].name, "region name", "ISCA-37406-Loss")

        # check that all regions are linked to the correct panel
        panel_regions = PanelRegion.objects.all()
        errors += len_check_wrapper(panel_regions, "panel regions", 4)
        first_panel_37_regions = panel_regions[0]
        first_panel_38_regions = panel_regions[1]
        second_panel_37_regions = panel_regions[2]
        second_panel_38_regions = panel_regions[3]

        errors += value_check_wrapper(
            first_panel_37_regions.panel,
            "first panel-region panel (ref 37)",
            self.first_panel,
        )
        errors += value_check_wrapper(
            first_panel_37_regions.region,
            "first panel-region region (ref 37)",
            regions[0],
        )
        errors += value_check_wrapper(
            first_panel_38_regions.panel,
            "first panel-region panel (ref 38)",
            self.first_panel,
        )
        errors += value_check_wrapper(
            first_panel_38_regions.region,
            "first panel-region region  (ref 38)",
            regions[1],
        )
        errors += value_check_wrapper(
            second_panel_37_regions.panel,
            "second panel-region panel (ref 37)",
            self.first_panel,
        )
        errors += value_check_wrapper(
            second_panel_37_regions.region,
            "second panel-region region (ref 37)",
            regions[2],
        )
        errors += value_check_wrapper(
            second_panel_38_regions.panel,
            "second panel-region panel (ref 38)",
            self.first_panel,
        )
        errors += value_check_wrapper(
            second_panel_38_regions.region,
            "second panel-region region  (ref 38)",
            regions[3],
        )

        errors = "".join(errors)
        assert not errors, errors


class TestInsertRegions_PreexistingRegion(TestCase):
    def setUp(self) -> None:
        """
        Scenario: a new panel has been made in the database
        No regions have been linked to it yet, at this point in the code
        One of the regions already exists in the database, emulating the situation
        where a region exists on multiple panels
        """
        self.first_panel = Panel.objects.create(
            external_id="162",
            panel_name="Severe microcephaly",
            panel_source="PanelApp",
            panel_version="4.31",
        )

        self.chromosome = Chromosome.objects.create(panelapp_name="16")

        self.confidence = Confidence.objects.create(confidence_level=3)

        self.moi = ModeOfInheritance.objects.create(mode_of_inheritance="TEST VALUE")

        self.mop = ModeOfPathogenicity.objects.create(mode_of_pathogenicity=None)

        self.variant_type = VariantType.objects.create(variant_type="cnv_test")

        self.haploinsufficiency = Haploinsufficiency.objects.create(
            haploinsufficiency=300
        )

        self.overlap = RequiredOverlap.objects.create(required_overlap=600)

        self.penetrance = Penetrance.objects.create(penetrance=None)

        self.triplosensitivity = Triplosensitivity.objects.create(triplosensitivity="")

        self.reference_genome = ReferenceGenome.objects.create(
            name="GRCh38"
        )

        self.first_region = Region.objects.create(
            name="ISCA-37406-Loss",
            verbose_name="16p13.3 region (includes CREBBP) Loss",
            chrom=self.chromosome,
            reference_genome=self.reference_genome,
            start=3725055,
            end=3880120,
            moi=self.moi,
            mop_id=self.mop.id,
            vartype=self.variant_type,
            confidence_id=self.confidence.id,
            haplo=self.haploinsufficiency,
            overlap=self.overlap,
            penetrance_id=self.penetrance.id,
            triplo=self.triplosensitivity,
            type="region",
        )

    def test_new_panel_linked_to_pre_existing_region(self):
        errors = []

        # make one of the test inputs for the function
        test_panel = PanelClass(
            id="162",
            name="Severe microcephaly",
            version="4.31",
            panel_source="PanelApp",
            genes=[],
            regions=[
                {
                    "gene_data": None,
                    "entity_type": "region",
                    "entity_name": "ISCA-37390-Loss",
                    "verbose_name": "5p15 terminal (Cri du chat syndrome) region Loss",
                    "confidence_level": "3",
                    "penetrance": "test_value",
                    "mode_of_pathogenicity": None,
                    "haploinsufficiency_score": "3",
                    "triplosensitivity_score": "test",
                    "required_overlap_percentage": 60,
                    "type_of_variants": "cnv_loss",
                    "mode_of_inheritance": "MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown",
                    "chromosome": "5",
                    "grch37_coordinates": None,
                    "grch38_coordinates": [37695, 11347150],
                },
                {
                    "gene_data": None,
                    "entity_type": "region",
                    "entity_name": "ISCA-37406-Loss",
                    "verbose_name": "16p13.3 region (includes CREBBP) Loss",
                    "confidence_level": "3",
                    "penetrance": None,
                    "mode_of_pathogenicity": None,
                    "haploinsufficiency_score": "300",
                    "triplosensitivity_score": "",
                    "required_overlap_percentage": 600,
                    "type_of_variants": "cnv_test",
                    "mode_of_inheritance": "TEST VALUE",
                    "chromosome": "16",
                    "grch37_coordinates": None,
                    "grch38_coordinates": [3725055, 3880120],
                },
            ],
        )

        _insert_regions(test_panel, self.first_panel)

        # check that the new region has been added to the database
        # and that the region which was already in the database isn't duplicated
        regions = Region.objects.all()
        errors += len_check_wrapper(regions, "regions", 2)

        errors += value_check_wrapper(
            regions[0].name, "name of first region", self.first_region.name
        )
        # the pre-populated value will show first
        errors += value_check_wrapper(
            regions[1].name, "name of second region", "ISCA-37390-Loss"
        )

        # check that both regions are linked to the correct panel
        panel_regions = PanelRegion.objects.all()
        errors += len_check_wrapper(panel_regions, "panel-regions", 2)
        errors += value_check_wrapper(
            panel_regions[0].panel, "first panel-regions' panel", self.first_panel
        )
        errors += value_check_wrapper(
            panel_regions[1].panel, "first panel-regions' panel", self.first_panel
        )

        errors = "".join(errors)
        assert not errors, errors


class TestInsertRegions_PreexistingLink(TestCase):
    def setUp(self) -> None:
        """
        Scenario: a panel has been made in the database
        One region is already linked to it, while the other isn't, emulating the situation
        where a panel is updated with region changes
        """
        self.first_panel = Panel.objects.create(
            external_id="162",
            panel_name="Severe microcephaly",
            panel_source="PanelApp",
            panel_version="4.31",
        )

        self.chromosome = Chromosome.objects.create(panelapp_name="16")

        self.confidence = Confidence.objects.create(confidence_level=3)

        self.moi = ModeOfInheritance.objects.create(mode_of_inheritance="TEST VALUE")

        self.mop = ModeOfPathogenicity.objects.create(mode_of_pathogenicity=None)

        self.variant_type = VariantType.objects.create(variant_type="cnv_test")

        self.haploinsufficiency = Haploinsufficiency.objects.create(
            haploinsufficiency=300
        )

        self.overlap = RequiredOverlap.objects.create(required_overlap=600)

        self.penetrance = Penetrance.objects.create(penetrance=None)

        self.triplosensitivity = Triplosensitivity.objects.create(triplosensitivity="")

        self.reference_genome = ReferenceGenome.objects.create(
            name="GRCh38"
        )

        self.first_region = Region.objects.create(
            name="ISCA-37406-Loss",
            verbose_name="16p13.3 region (includes CREBBP) Loss",
            chrom=self.chromosome,
            reference_genome=self.reference_genome,
            start=3725055,
            end=3880120,
            moi=self.moi,
            mop_id=self.mop.id,
            vartype=self.variant_type,
            confidence_id=self.confidence.id,
            haplo=self.haploinsufficiency,
            overlap=self.overlap,
            penetrance_id=self.penetrance.id,
            triplo=self.triplosensitivity,
            type="region",
        )

        self.first_panel_region_link = PanelRegion.objects.create(
            region=self.first_region,
            panel=self.first_panel,
            justification="test_justification",
        )

    def test_pre_existing_panel_region_link(self):
        errors = []

        # make one of the test inputs for the function
        test_panel = PanelClass(
            id="162",
            name="Severe microcephaly",
            version="4.31",
            panel_source="PanelApp",
            genes=[],
            regions=[
                {
                    "gene_data": None,
                    "entity_type": "region",
                    "entity_name": "ISCA-37390-Loss",
                    "verbose_name": "5p15 terminal (Cri du chat syndrome) region Loss",
                    "confidence_level": "3",
                    "penetrance": "test_value",
                    "mode_of_pathogenicity": None,
                    "haploinsufficiency_score": "3",
                    "triplosensitivity_score": "test",
                    "required_overlap_percentage": 60,
                    "type_of_variants": "cnv_loss",
                    "mode_of_inheritance": "MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown",
                    "chromosome": "5",
                    "grch37_coordinates": None,
                    "grch38_coordinates": [37695, 11347150],
                },
                {
                    "gene_data": None,
                    "entity_type": "region",
                    "entity_name": "ISCA-37406-Loss",
                    "verbose_name": "16p13.3 region (includes CREBBP) Loss",
                    "confidence_level": "3",
                    "penetrance": None,
                    "mode_of_pathogenicity": None,
                    "haploinsufficiency_score": "300",
                    "triplosensitivity_score": "",
                    "required_overlap_percentage": 600,
                    "type_of_variants": "cnv_test",
                    "mode_of_inheritance": "TEST VALUE",
                    "chromosome": "16",
                    "grch37_coordinates": None,
                    "grch38_coordinates": [3725055, 3880120],
                },
            ],
        )

        _insert_regions(test_panel, self.first_panel)

        # check that the new region has been added to the database
        # and that the region which was already in the database isn't duplicated
        regions = Region.objects.all()

        errors += len_check_wrapper(regions, "regions", 2)
        errors += value_check_wrapper(
            regions[0].name, "name of first region", self.first_region.name
        )  # the pre-populated value will show first
        errors += value_check_wrapper(
            regions[1].name, "name of second region", "ISCA-37390-Loss"
        )

        # check that both regions are linked to the correct panel
        # the first link in PanelRegion will be the one we made in set-up
        panel_regions = PanelRegion.objects.all()
        errors += len_check_wrapper(panel_regions, "panel-regions", 2)
        errors += value_check_wrapper(
            panel_regions[0], "first panel-region", self.first_panel_region_link
        )
        errors += value_check_wrapper(
            panel_regions[1].panel, "second panel-region's panel", self.first_panel
        )

        errors = "".join(errors)
        assert not errors, errors
