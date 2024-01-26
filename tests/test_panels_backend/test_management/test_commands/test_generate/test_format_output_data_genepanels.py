from django.test import TestCase

from panels_backend.management.commands.generate import Command


class TestFormatOutputDataGenepanels(TestCase):
    def test_straightforward_case(self):
        """
        CASE: Two Clinical Indications are provided with links to 1 panel each. Each panel contains 2 genes.
        None of the genes are on the 'exclude' list (e.g. due to being mitochondrial).
        EXPECT: Return a 4-entry list-of-lists which captures the CI's R code/name, the panel's name and version,
        the HGNC, and the PanelApp version on each line.
        """
        ci_panels = {
            "R123.2": [
                {
                    "ci_panel__clinical_indication__r_code": "R1",
                    "ci_panel__clinical_indication_id__name": "Condition 1",
                    "ci_panel__panel_id": 1,
                    "ci_panel__panel__external_id": "109",
                    "ci_panel__panel__panel_name": "First Panel",
                    "ci_panel__panel__panel_version": "5",
                }
            ],
            "R2": [
                {
                    "ci_panel__clinical_indication__r_code": "R2",
                    "ci_panel__clinical_indication_id__name": "Condition 2",
                    "ci_panel__panel_id": 2,
                    "ci_panel__panel__external_id": "209",
                    "ci_panel__panel__panel_name": "Second Panel",
                    "ci_panel__panel__panel_version": "2",
                }
            ],
        }

        panel_genes = {1: ["HGNC:1", "HGNC:2"], 2: ["HGNC:3", "HGNC:4"]}
        excluded_hgncs = set([])
        cmd = Command()
        actual = cmd._format_output_data_genepanels(
            ci_panels, panel_genes, excluded_hgncs
        )
        expected = [
            ["R123.2_Condition 1", "First Panel_5.0", "HGNC:1", "109"],
            ["R123.2_Condition 1", "First Panel_5.0", "HGNC:2", "109"],
            ["R2_Condition 2", "Second Panel_2.0", "HGNC:3", "209"],
            ["R2_Condition 2", "Second Panel_2.0", "HGNC:4", "209"],
        ]
        self.assertEqual(expected, actual)

    def test_includes_non_panelapp_panel(self):
        """
        CASE: Two Clinical Indications are provided with links to 1 panel each. Each panel contains 2 genes.
        None of the genes are on the 'exclude' list (e.g. due to being mitochondrial).
        One panel is from PanelApp, one isn't
        EXPECT: Return a 4-entry list-of-lists which captures the CI's R code/name, the panel's name and version,
        the HGNC, and the PanelApp version on each line. For the NOT PanelApp-derived panel, then the PanelApp version
        will be a blank line.
        """
        ci_panels = {
            "R123.2": [
                {
                    "ci_panel__clinical_indication__r_code": "R1",
                    "ci_panel__clinical_indication_id__name": "Condition 1",
                    "ci_panel__panel_id": 1,
                    "ci_panel__panel__external_id": "109",
                    "ci_panel__panel__panel_name": "First Panel",
                    "ci_panel__panel__panel_version": "5",
                }
            ],
            "R2": [
                {
                    "ci_panel__clinical_indication__r_code": "R2",
                    "ci_panel__clinical_indication_id__name": "Condition 2",
                    "ci_panel__panel_id": 2,
                    "ci_panel__panel__external_id": None,
                    "ci_panel__panel__panel_name": "HGNC:3&HGNC:4",
                    "ci_panel__panel__panel_version": "1.0",
                }
            ],
        }

        panel_genes = {1: ["HGNC:1", "HGNC:2"], 2: ["HGNC:3", "HGNC:4"]}
        excluded_hgncs = set([])
        cmd = Command()
        actual = cmd._format_output_data_genepanels(
            ci_panels, panel_genes, excluded_hgncs
        )
        expected = [
            ["R123.2_Condition 1", "First Panel_5.0", "HGNC:1", "109"],
            ["R123.2_Condition 1", "First Panel_5.0", "HGNC:2", "109"],
            ["R2_Condition 2", "HGNC:3&HGNC:4_1.0", "HGNC:3", ""],
            ["R2_Condition 2", "HGNC:3&HGNC:4_1.0", "HGNC:4", ""],
        ]
        self.assertEqual(expected, actual)

    def test_one_hgnc_on_exclude_list(self):
        """
        CASE: Two Clinical Indications are provided with links to 1 panel each. Each panel contains 2 genes.
        ONE of the genes is on the 'exclude' list (e.g. due to being mitochondrial).
        EXPECT: Return a 3-entry list-of-lists which captures the CI's R code/name, the panel's name and version,
        the HGNC, and the PanelApp panel ID on each line. The line for the 'exclude' list HGNC isn't present.
        """
        ci_panels = {
            "R123.2": [
                {
                    "ci_panel__clinical_indication__r_code": "R1",
                    "ci_panel__clinical_indication_id__name": "Condition 1",
                    "ci_panel__panel_id": 1,
                    "ci_panel__panel__external_id": "109",
                    "ci_panel__panel__panel_name": "First Panel",
                    "ci_panel__panel__panel_version": "5",
                }
            ],
            "R2": [
                {
                    "ci_panel__clinical_indication__r_code": "R2",
                    "ci_panel__clinical_indication_id__name": "Condition 2",
                    "ci_panel__panel_id": 2,
                    "ci_panel__panel__external_id": "209",
                    "ci_panel__panel__panel_name": "Second Panel",
                    "ci_panel__panel__panel_version": "2",
                }
            ],
        }

        panel_genes = {1: ["HGNC:1", "HGNC:2"], 2: ["HGNC:3", "HGNC:4"]}
        excluded_hgncs = set(["HGNC:1"])
        cmd = Command()
        actual = cmd._format_output_data_genepanels(
            ci_panels, panel_genes, excluded_hgncs
        )
        expected = [
            ["R123.2_Condition 1", "First Panel_5.0", "HGNC:2", "109"],
            ["R2_Condition 2", "Second Panel_2.0", "HGNC:3", "209"],
            ["R2_Condition 2", "Second Panel_2.0", "HGNC:4", "209"],
        ]
        self.assertEqual(expected, actual)
