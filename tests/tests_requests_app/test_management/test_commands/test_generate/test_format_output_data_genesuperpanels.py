from django.test import TestCase

from requests_app.management.commands.generate import Command


class TestFormatGeneSuperPanels(TestCase):
    def test_format_gene_superpanels_basic(self):
        """
        
        """

        exclude=[]
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

        superpanel_genes = {1: set(["HGNC:910", "HGNC:300"]),
                            2: set(["HGNC:100", "HGNC:300"])}

        expected = [
            ["R1_Condition 1", "First Panel_5.0", "HGNC:300"],
            ["R1_Condition 1", "First Panel_5.0", "HGNC:910"],
            ["R2_Condition 2", "Second Panel_2.0", "HGNC:100"],
            ["R2_Condition 2", "Second Panel_2.0", "HGNC:300"],
        ]

        cmd = Command()
        actual = cmd._format_output_data_genesuperpanels(ci_superpanels, superpanel_genes, exclude)
        
        self.assertEqual(expected, actual)