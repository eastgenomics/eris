"""
Tested scenario `insert_data_into_db_function`
- core function of inserting panel and their metadata
- flag previous and current clinical indication-panel link for review if panel name or panel version change in PanelApp API
- nothing change if panel remains the same in PanelApp API


- does not test for panel-gene changes - this is dealt with in `insert_gene`
"""

from django.test import TestCase
from requests_app.management.commands.panelapp import PanelClass
from requests_app.models import (
    Panel,
    ClinicalIndication,
    ClinicalIndicationPanel,
    PanelGene,
)
from requests_app.management.commands.utils import sortable_version

from requests_app.management.commands._insert_panel import insert_data_into_db


class TestInsertDataIntoDB(TestCase):
    def setUp(self) -> None:
        """
        setup conditions for the test
        """
        self.first_panel = Panel.objects.create(
            external_id="1141",
            panel_name="Acute rhabdomyolosis",
            panel_source="PanelApp",
            panel_version=sortable_version("1.15"),
        )

        self.first_clinical_indication = ClinicalIndication.objects.create(
            r_code="R123",
            name="Test clinical indication",
            test_method="Test method",
        )

        self.first_link = ClinicalIndicationPanel.objects.create(
            config_source="Test config source",
            td_version=None,
            clinical_indication_id=self.first_clinical_indication.id,
            panel_id=self.first_panel.id,
            current=True,
        )

    def test_that_a_new_panel_will_be_inserted_together_with_its_gene(
        self,
    ):
        """
        test that the core function of `insert_data_to_db` works - insert panel + their metadata
        """
        errors = []

        mock_api = PanelClass(
            id="1142",  # note the different external-id
            name="Acute rhabdomyolyosis",
            version="1.15",
            panel_source="PanelApp",
            genes=[
                {
                    "gene_data": {
                        "hgnc_id": 21497,
                        "gene_name": "acyl-CoA dehydrogenase family member 9",
                        "gene_symbol": "ACAD9",
                        "alias": ["NPD002", "MGC14452"],
                    },
                    "confidence_level": 3,
                    "mode_of_inheritance": "test",
                    "mode_of_pathogenicity": "test",
                    "penetrance": "test",
                }
            ],
            regions=[],
        )

        insert_data_into_db(mock_api, "PanelApp")

        if ClinicalIndicationPanel.objects.all().count() != 1:
            errors.append(
                "Expected 1 ClinicalIndicationPanel objects"
            )  # assert that there is no new clinical indication-panel (just the one we created in setup)

        if Panel.objects.all().count() != 2:
            errors.append(
                "Expected 2 Panel objects"
            )  # first one is the one we made in setup, second one is inserted

        panels = Panel.objects.all()
        attached_gene_hgnc_id = PanelGene.objects.filter(panel_id=panels[1].id).values(
            "gene_id__hgnc_id"
        )

        if (
            not attached_gene_hgnc_id
            or attached_gene_hgnc_id[0]["gene_id__hgnc_id"] != "21497"
        ):
            errors.append(
                "Expected second panel to be attached to hgnc-id 21497"
            )  # assert that the second panel that is inserted is attached to gene hgnc-id 21497 through PanelGene

        assert not errors, errors

    def test_that_previous_clinical_indication_panel_is_flagged_when_panel_version_change(
        self,
    ):
        """
        example scenario (panel version upgrade):
        - first panel and first clinical indication is already linked in the database
        - second panel comes in with the same external-id but different version
        - we expect the `insert_data_into_db` to flag previous link between first panel and first clinical indication for review
        - also to create a new link between second panel and first clinical indication for review
        """
        errors = []

        mock_api = PanelClass(
            id="1141",
            name="Acute rhabdomyolyosis",
            version="1.16",  # note version change
            panel_source="PanelApp",
            genes=[
                {
                    "gene_data": {
                        "hgnc_id": 21497,
                        "gene_name": "acyl-CoA dehydrogenase family member 9",
                        "gene_symbol": "ACAD9",
                        "alias": ["NPD002", "MGC14452"],
                    },
                    "confidence_level": 3,
                    "mode_of_inheritance": "test",
                    "mode_of_pathogenicity": "test",
                    "penetrance": "test",
                }
            ],
            regions=[],
        )

        insert_data_into_db(mock_api, "PanelApp")

        if ClinicalIndicationPanel.objects.all().count() != 2:
            errors.append(
                "Expected 2 ClinicalIndicationPanel objects"
            )  # assert that there is one new clinical indication-panel

        clinical_indication_panels = ClinicalIndicationPanel.objects.all()

        if (
            not clinical_indication_panels[0].pending
            or not clinical_indication_panels[1].pending
        ):
            errors.append(
                "Expected both ClinicalIndicationPanel to be flagged for review"  # assert that both clinical indication-panels are flagged
            )

        if Panel.objects.all().count() != 2:
            errors.append(
                "Expected 2 Panel objects"
            )  # assert that the panel with a different version is inserted

        panels = Panel.objects.all()
        if not panels[1].panel_version == sortable_version(
            "1.16"
        ):  # assert second panel is the inserted panel
            errors.append("Expected second panel to be version 1.16")

        assert not errors, errors

    def test_that_previous_clinical_indication_panel_is_flagged_when_panel_name_change(
        self,
    ):
        """
        example scenario (panel version upgrade):
        - first panel and first clinical indication is already linked in the database
        - second panel comes in with the same external-id but different panel name
        - we expect the `insert_data_into_db` to flag previous link between first panel and first clinical indication for review
        - also to create a new link between second panel and first clinical indication for review
        """
        errors = []

        mock_api = PanelClass(
            id="1141",
            name="Acute rhabdomyolosis with a different name",  # note the different name
            version="1.15",
            panel_source="PanelApp",
            genes=[
                {
                    "gene_data": {
                        "hgnc_id": 21497,
                        "gene_name": "acyl-CoA dehydrogenase family member 9",
                        "gene_symbol": "ACAD9",
                        "alias": ["NPD002", "MGC14452"],
                    },
                    "confidence_level": 3,
                    "mode_of_inheritance": "test",
                    "mode_of_pathogenicity": "test",
                    "penetrance": "test",
                }
            ],
            regions=[],
        )

        insert_data_into_db(mock_api, "PanelApp")

        if ClinicalIndicationPanel.objects.all().count() != 2:
            errors.append(
                "Expected 2 ClinicalIndicationPanel objects"
            )  # assert that there is a new clinical indication-panel

        clinical_indication_panels = ClinicalIndicationPanel.objects.all()

        if (
            not clinical_indication_panels[0].pending
            or not clinical_indication_panels[1].pending
        ):
            errors.append(
                "Expected both ClinicalIndicationPanel to be flagged for review"  # assert that both clinical indication-panels are flagged
            )

        if Panel.objects.all().count() != 2:
            errors.append(
                "Expected 2 Panel objects"
            )  # assert that the panel with a different version is inserted

        panels = Panel.objects.all()
        if (
            not panels[1].panel_name == "Acute rhabdomyolosis with a different name"
        ):  # assert second panel is the inserted panel
            errors.append(
                "Expected second panel to have a different name - Acute rhabdomyolosis with a different name"
            )

        assert not errors, errors

    def test_that_nothing_change_if_panel_remains_the_same_in_panelapp_api(
        self,
    ):
        """
        example scenario:
        - if the panel remains the same in panelapp api, we expect nothing to change in the database
        - this function does not deal with panel-gene changes, which is dealt with in `insert_gene`
        """
        errors = []

        mock_api = PanelClass(
            id=1141,
            name="Acute rhabdomyolosis",
            version=1.15,
            panel_source="PanelApp",
            genes=[
                {
                    "gene_data": {
                        "hgnc_id": 21497,
                        "gene_name": "acyl-CoA dehydrogenase family member 9",
                        "gene_symbol": "ACAD9",
                        "alias": ["NPD002", "MGC14452"],
                    },
                    "confidence_level": 3,
                    "mode_of_inheritance": "test",
                    "mode_of_pathogenicity": "test",
                    "penetrance": "test",
                }
            ],
            regions=[],
        )

        insert_data_into_db(mock_api, "PanelApp")

        if Panel.objects.all().count() != 1:
            errors.append(
                "Expected only 1 Panel objects"
            )  # assert only one Panel in db

        panels = Panel.objects.all()
        if (
            not panels[0].panel_name == "Acute rhabdomyolosis"
        ):  # assert nothing has changed to the existing panel
            errors.append("Expected the only panel to have the same name")

        assert not errors, errors
