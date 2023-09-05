from django.test import TestCase
from django.db.models import QuerySet
from django_mock_queries.query import MockSet, MockModel

from requests_app.models import \
    Panel, Confidence, ModeOfInheritance, \
    Penetrance, ModeOfPathogenicity, Region, PanelRegion, VariantType, \
    Haploinsufficiency, RequiredOverlap, Triplosensitivity

from requests_app.management.commands._insert_panel import \
    _insert_regions

from requests_app.management.commands.panelapp import PanelClass


## _insert_regions
class TestInsertRegions_NewRegion(TestCase):
    def setUp(self) -> None:
        """
        Scenario: a new panel has been made in the database
        No regions have been linked to it yet, at this point in the code
        """
        self.first_panel = Panel.objects.create(
            external_id="162", \
            panel_name="Severe microcephaly", \
            panel_source="PanelApp", \
            panel_version="4.31"
        )


    def test_new_panel_linked_to_acceptable_region(self):
        # make one of the test inputs for the function        
        test_panel = PanelClass(
            id="162", 
            name="Severe microcephaly", 
            version="4.31",
            panel_source="PanelApp",
            genes=[],
            regions=
            [
                {"gene_data": None,
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
                "grch38_coordinates": [
                    37695,
                    11347150
                ],
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
                "grch38_coordinates": [
                    3725055,
                    3880120
                    ] 
                }
            ]
        )

        _insert_regions(test_panel, self.first_panel)

        # check that both regions have been added to the database
        regions = Region.objects.all()
        assert len(regions) == 2
        assert regions[0].name == "ISCA-37390-Loss"
        assert regions[1].name == "ISCA-37406-Loss"


        # check that both regions are linked to the correct panel
        panel_regions = PanelRegion.objects.all()
        assert len(panel_regions) == 2
        first_panel_regions = panel_regions[0]
        second_panel_regions = panel_regions[1]
        assert first_panel_regions.panel == self.first_panel
        assert first_panel_regions.region == regions[0]
        assert second_panel_regions.panel == self.first_panel
        assert second_panel_regions.region == regions[1]
        

class TestInsertRegions_PreexistingRegion(TestCase):
    def setUp(self) -> None:
        """
        Scenario: a new panel has been made in the database
        No regions have been linked to it yet, at this point in the code
        One of the regions already exists in the database, emulating the situation
        where a region exists on multiple panels 
        """
        self.first_panel = Panel.objects.create(
            external_id="162", \
            panel_name="Severe microcephaly", \
            panel_source="PanelApp", \
            panel_version="4.31"
        )


        self.confidence = Confidence.objects.create(
            confidence_level=3
        )

        self.moi = ModeOfInheritance.objects.create(
            mode_of_inheritance="TEST VALUE"
        )

        self.mop = ModeOfPathogenicity.objects.create(
            mode_of_pathogenicity=None
        )

        self.variant_type = VariantType.objects.create(
            variant_type="cnv_test"
        )

        self.haploinsufficiency = Haploinsufficiency.objects.create(
            haploinsufficiency=300
        )

        self.overlap = RequiredOverlap.objects.create(
            required_overlap=600
        )

        self.penetrance = Penetrance.objects.create(
            penetrance=None
        )

        self.triplosensitivity = Triplosensitivity.objects.create(
            triplosensitivity = ""
        )

        self.first_region = Region.objects.create(
            name="ISCA-37406-Loss",
            verbose_name="16p13.3 region (includes CREBBP) Loss",
            chrom="16",
            start_37=None,
            end_37=None,
            start_38=3725055,
            end_38=3880120,
            moi=self.moi,
            mop_id=self.mop.id,
            vartype=self.variant_type,
            confidence_id=self.confidence.id,
            haplo=self.haploinsufficiency,
            overlap=self.overlap,
            penetrance_id=self.penetrance.id,
            triplo=self.triplosensitivity,
            type="region"
        )


    def test_new_panel_linked_to_pre_existing_region(self):
        # make one of the test inputs for the function        
        test_panel = PanelClass(
            id="162", 
            name="Severe microcephaly", 
            version="4.31",
            panel_source="PanelApp",
            genes=[],
            regions=
            [
                {"gene_data": None,
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
                "grch38_coordinates": [
                    37695,
                    11347150
                ],
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
                "grch38_coordinates": [
                    3725055,
                    3880120
                    ] 
                }
            ]
        )

        _insert_regions(test_panel, self.first_panel)

        # check that the new region has been added to the database
        # and that the region which was already in the database isn't duplicated
        regions = Region.objects.all()

        assert len(regions) == 2 

        assert regions[0].name == self.first_region.name # the pre-populated value will show first
        assert regions[1].name == "ISCA-37390-Loss"


        # check that both regions are linked to the correct panel
        panel_regions = PanelRegion.objects.all()
        assert len(panel_regions) == 2
        assert panel_regions[0].panel == self.first_panel
        assert panel_regions[1].panel == self.first_panel


class TestInsertRegions_PreexistinLink(TestCase):
    def setUp(self) -> None:
        """
        Scenario: a panel has been made in the database
        One region is already linked to it, while the other isn't, emulating the situation
        where a panel is updated with region changes
        """
        self.first_panel = Panel.objects.create(
            external_id="162", \
            panel_name="Severe microcephaly", \
            panel_source="PanelApp", \
            panel_version="4.31"
        )


        self.confidence = Confidence.objects.create(
            confidence_level=3
        )

        self.moi = ModeOfInheritance.objects.create(
            mode_of_inheritance="TEST VALUE"
        )

        self.mop = ModeOfPathogenicity.objects.create(
            mode_of_pathogenicity=None
        )

        self.variant_type = VariantType.objects.create(
            variant_type="cnv_test"
        )

        self.haploinsufficiency = Haploinsufficiency.objects.create(
            haploinsufficiency=300
        )

        self.overlap = RequiredOverlap.objects.create(
            required_overlap=600
        )

        self.penetrance = Penetrance.objects.create(
            penetrance=None
        )

        self.triplosensitivity = Triplosensitivity.objects.create(
            triplosensitivity = ""
        )

        self.first_region = Region.objects.create(
            name="ISCA-37406-Loss",
            verbose_name="16p13.3 region (includes CREBBP) Loss",
            chrom="16",
            start_37=None,
            end_37=None,
            start_38=3725055,
            end_38=3880120,
            moi=self.moi,
            mop_id=self.mop.id,
            vartype=self.variant_type,
            confidence_id=self.confidence.id,
            haplo=self.haploinsufficiency,
            overlap=self.overlap,
            penetrance_id=self.penetrance.id,
            triplo=self.triplosensitivity,
            type="region"
        )

        self.first_panel_region_link = PanelRegion.objects.create(
            region=self.first_region,
            panel=self.first_panel,
            justification="test_justification"
        )


    def test_pre_existing_panel_region_link(self):
        # make one of the test inputs for the function        
        test_panel = PanelClass(
            id="162", 
            name="Severe microcephaly", 
            version="4.31",
            panel_source="PanelApp",
            genes=[],
            regions=
            [
                {"gene_data": None,
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
                "grch38_coordinates": [
                    37695,
                    11347150
                ],
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
                "grch38_coordinates": [
                    3725055,
                    3880120
                    ] 
                }
            ]
            
        )

        _insert_regions(test_panel, self.first_panel)

        # check that the new region has been added to the database
        # and that the region which was already in the database isn't duplicated
        regions = Region.objects.all()

        assert len(regions) == 2 

        assert regions[0].name == self.first_region.name # the pre-populated value will show first
        assert regions[1].name == "ISCA-37390-Loss"


        # check that both regions are linked to the correct panel
        # the first link in PanelRegion will be the one we made in set-up
        panel_regions = PanelRegion.objects.all()
        assert len(panel_regions) == 2
        assert panel_regions[0] == self.first_panel_region_link
        assert panel_regions[1].panel == self.first_panel

