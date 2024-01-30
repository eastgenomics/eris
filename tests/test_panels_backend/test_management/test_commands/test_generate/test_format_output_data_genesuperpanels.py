from django.test import TestCase

from panels_backend.management.commands.generate import Command


class TestFormatGeneSuperPanels(TestCase):
    def test_format_gene_superpanels_basic(self):
        """
        CASE: Two Clinical Indications are provided with links to 1 SuperPanel each.
        Each SuperPanel contains 2 genes.
        None of the genes are on the 'exclude' list (e.g. due to being mitochondrial).
        EXPECT: Return a 4-entry list-of-lists which captures the CI's R code/name, the superpanel's name and version,
        and the HGNC on each line.
        """
        exclude = []
        ci_superpanels = {
            "R1": [
                {
                    "ci_superpanel__clinical_indication__r_code": "R1",
                    "ci_superpanel__clinical_indication__name": "Condition 1",
                    "ci_superpanel__superpanel": 1,
                    "ci_superpanel__superpanel__external_id": "109",
                    "ci_superpanel__superpanel__panel_name": "First Panel",
                    "ci_superpanel__superpanel__panel_version": "5",
                }
            ],
            "R2": [
                {
                    "ci_superpanel__clinical_indication__r_code": "R2",
                    "ci_superpanel__clinical_indication__name": "Condition 2",
                    "ci_superpanel__superpanel": 2,
                    "ci_superpanel__superpanel__external_id": "209",
                    "ci_superpanel__superpanel__panel_name": "Second Panel",
                    "ci_superpanel__superpanel__panel_version": "2",
                }
            ],
        }

        superpanel_genes = {
            1: set(["HGNC:910", "HGNC:300"]),
            2: set(["HGNC:100", "HGNC:300"]),
        }

        expected = [
            ["R1_Condition 1", "First Panel_5.0", "HGNC:300", "109"],
            ["R1_Condition 1", "First Panel_5.0", "HGNC:910", "109"],
            ["R2_Condition 2", "Second Panel_2.0", "HGNC:100", "209"],
            ["R2_Condition 2", "Second Panel_2.0", "HGNC:300", "209"],
        ]

        cmd = Command()
        actual = cmd._format_output_data_genesuperpanels(
            ci_superpanels, superpanel_genes, exclude
        )

        self.assertEqual(expected, actual)

    def test_one_hgnc_on_exclude_list(self):
        """
        CASE: Two Clinical Indications are provided with links to 1 superpanel each. Each superpanel contains 2 genes.
        ONE of the genes is on the 'exclude' list (e.g. due to being mitochondrial).
        EXPECT: Return a 2-entry list-of-lists which captures the CI's R code/name, the superpanel's name and version,
        and the HGNC on each line. The lines for the 'exclude' list's HGNC isn't present.
        """
        exclude = ["HGNC:300"]  # note excluded HGNC here
        ci_superpanels = {
            "R1": [
                {
                    "ci_superpanel__clinical_indication__r_code": "R1",
                    "ci_superpanel__clinical_indication__name": "Condition 1",
                    "ci_superpanel__superpanel": 1,
                    "ci_superpanel__superpanel__external_id": "109",
                    "ci_superpanel__superpanel__panel_name": "First Panel",
                    "ci_superpanel__superpanel__panel_version": "5",
                }
            ],
            "R2": [
                {
                    "ci_superpanel__clinical_indication__r_code": "R2",
                    "ci_superpanel__clinical_indication__name": "Condition 2",
                    "ci_superpanel__superpanel": 2,
                    "ci_superpanel__superpanel__external_id": "209",
                    "ci_superpanel__superpanel__panel_name": "Second Panel",
                    "ci_superpanel__superpanel__panel_version": "2",
                }
            ],
        }

        superpanel_genes = {
            1: set(["HGNC:910", "HGNC:300"]),
            2: set(["HGNC:100", "HGNC:300"]),
        }

        expected = [
            ["R1_Condition 1", "First Panel_5.0", "HGNC:910", "109"],
            ["R2_Condition 2", "Second Panel_2.0", "HGNC:100", "209"],
        ]

        cmd = Command()
        actual = cmd._format_output_data_genesuperpanels(
            ci_superpanels, superpanel_genes, exclude
        )

        self.assertEqual(expected, actual)
