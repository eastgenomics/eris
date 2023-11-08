from django.test import TestCase

from requests_app.management.commands.history import History
from requests_app.management.commands._parse_transcript import _make_hgnc_gene_sets
from tests.tests_requests_app.test_management.test_commands.test_insert_ci.test_insert_test_directory_data import (
    len_check_wrapper,
    value_check_wrapper,
)
from requests_app.models import (
    Gene,
    HgncRelease,
    GeneHgncRelease,
    GeneHgncReleaseHistory,
)


class TestMakeHgncGeneSets_AllScenarios(TestCase):
    """
    CASE: Provide a mix of all expected types of case:
        - some genes are new and not in db
        - some genes are already in db
        - of genes in the db, some are unchanged, some have a changed alias, some have a changed
          symbol, some have both alias and symbol changes

    EXPECT: The genes in the cases outlined above, are placed in the correct categories and returned.
    """

    def setUp(self) -> None:
        # genes 1-3 below have changes in the new HGNC file
        self.gene_one = Gene.objects.create(
            hgnc_id="HGNC:100", gene_symbol="ABC1", alias_symbols="Alias,One"
        )
        self.gene_two = Gene.objects.create(
            hgnc_id="HGNC:200", gene_symbol="DEF1", alias_symbols="Alias,Two"
        )
        self.gene_three = Gene.objects.create(
            hgnc_id="HGNC:300", gene_symbol="GHI1", alias_symbols="Alias,Three"
        )
        # gene_four will be entirely unchanged in the new HGNC file
        self.gene_four = Gene.objects.create(
            hgnc_id="HGNC:400", gene_symbol="JKL1", alias_symbols="Alias,Four"
        )
        # gene_five isn't in the new HGNC file at all - it was added as part of an earlier release
        self.gene_five = Gene.objects.create(
            hgnc_id="HGNC:500", gene_symbol="MNO1", alias_symbols="Alias,Five"
        )

    def test_four_categories(self):
        hgnc_id_to_symbol = {
            "HGNC:100": "new_symbol",  # HGNC:100 symbol change
            "HGNC:200": "DEF1",
            "HGNC:300": "not_GHI1",  # HGNC:300 symbol and alias both changed
            "HGNC:400": "JKL1",
            "HGNC:600": "PQR1",
        }  # HGNC:600 is new to this release, and not in the db
        hgnc_id_to_alias = {
            "HGNC:100": ["Alias", "One"],
            "HGNC:200": ["new", "alias"],  # HGNC:200 alias change
            "HGNC:300": [
                "not_Alias",
                "Three",
            ],  # HGNC:300 symbol and alias both changed
            "HGNC:400": ["Alias", "Four"],
            "HGNC:600": ["Alias", "Six"],
        }  # HGNC:600 is new to this release, and not in the db

        (
            new_hgncs,
            hgnc_symbol_changed,
            hgnc_alias_changed,
            unchanged,
        ) = _make_hgnc_gene_sets(hgnc_id_to_symbol, hgnc_id_to_alias)

        self.assertDictEqual(
            new_hgncs[0],
            {"hgnc_id": "HGNC:600", "symbol": "PQR1", "alias": "Alias,Six"},
        )
        self.assertDictEqual(
            hgnc_symbol_changed, {"HGNC:100": "new_symbol", "HGNC:300": "not_GHI1"}
        )
        self.assertDictEqual(
            hgnc_alias_changed, {"HGNC:200": "new,alias", "HGNC:300": "not_Alias,Three"}
        )
        assert unchanged == ["HGNC:400"]
