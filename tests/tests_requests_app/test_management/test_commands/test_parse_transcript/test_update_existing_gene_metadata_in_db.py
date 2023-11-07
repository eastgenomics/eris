from django.test import TestCase
import numpy as np

from requests_app.models import Gene, HgncRelease, GeneHgncRelease, GeneHgncReleaseHistory

from requests_app.management.commands._parse_transcript import (
    _update_existing_gene_metadata_symbol_in_db,
    _update_existing_gene_metadata_aliases_in_db,
)


class TestUpdateExistingGeneSymbol(TestCase):
    """
    Test various cases on _update_existing_gene_metadata_symbol_in_db
    """

    def setUp(self) -> None:
        # Populate the Gene test database with some easy examples
        self.FAM234A = Gene.objects.create(
            hgnc_id="14163",
            gene_symbol="FAM234A",
            alias_symbols="DKFZP761D0211,FLJ32603",
        )

        Gene.objects.create(
            hgnc_id="12713", gene_symbol="VPS41", alias_symbols="HVSP41"
        )

        Gene.objects.create(hgnc_id="50000", gene_symbol="YFP1", alias_symbols="ABC")

        Gene.objects.create(
            hgnc_id="51000", gene_symbol="YFP2", alias_symbols="ABCD,EFGH"
        )

        self.gene_blank = Gene.objects.create(
            hgnc_id="50", gene_symbol=None, alias_symbols=None
        )

        self.hgnc_release = HgncRelease.objects.create(
            hgnc_release="hgnc_v1"
        )

        self.user = "test_user"

    def test_no_changes(self):
        """
        A gene is unchanged
        """
        test_hgnc_approved = {"14163": "FAM234A"}
        _update_existing_gene_metadata_symbol_in_db(test_hgnc_approved, self.hgnc_release,
                                                    self.user)

        # check that the entry isn't changed from how it was at set-up
        gene_db = Gene.objects.filter(hgnc_id="14163")
        assert len(gene_db) == 1
        assert gene_db[0].hgnc_id == self.FAM234A.hgnc_id
        assert gene_db[0].gene_symbol == self.FAM234A.gene_symbol

    def test_approved_name_change(self):
        """
        Test case: the approved name has changed for a gene, since last update
        """
        made_up_approved_name = "FAM234A_test"
        test_hgnc_approved = {"14163": made_up_approved_name}
        _update_existing_gene_metadata_symbol_in_db(test_hgnc_approved, self.hgnc_release,
                                                    self.user)

        # check that the entry for 14163 in the Gene test datatable is updated
        gene_db = Gene.objects.filter(hgnc_id="14163")
        assert len(gene_db) == 1
        assert gene_db[0].gene_symbol == made_up_approved_name

    def test_approved_names_change_several(self):
        """
        Test case: the approved name has changed for several genes, since last
        update
        """
        made_up_approved_name = "FAM234A_test"
        made_up_approved_name_two = "test_nonsense"

        test_hgnc_approved = {
            "14163": made_up_approved_name,
            "12713": made_up_approved_name_two,
        }
        _update_existing_gene_metadata_symbol_in_db(test_hgnc_approved, self.hgnc_release,
                                                    self.user)

        # check that the entry for 14163 in the Gene test datatable is updated
        gene_db = Gene.objects.filter(hgnc_id="14163")
        assert len(gene_db) == 1
        assert gene_db[0].gene_symbol == made_up_approved_name

        gene_db = Gene.objects.filter(hgnc_id="12713")
        assert len(gene_db) == 1
        assert gene_db[0].gene_symbol == made_up_approved_name_two


class TestUpdateExistingAliasSymbol(TestCase):
    """
    Test various cases on _update_existing_gene_metadata_aliases_in_db
    """

    def setUp(self) -> None:
        # Populate the Gene test database with some easy examples
        self.FAM234A = Gene.objects.create(
            hgnc_id="14163",
            gene_symbol="FAM234A",
            alias_symbols="DKFZP761D0211,FLJ32603",
        )

        Gene.objects.create(
            hgnc_id="12713", gene_symbol="VPS41", alias_symbols="HVSP41"
        )

        Gene.objects.create(hgnc_id="50000", gene_symbol="YFP1", alias_symbols="ABC")

        Gene.objects.create(
            hgnc_id="51000", gene_symbol="YFP2", alias_symbols="ABCD,EFGH"
        )

        self.gene_blank = Gene.objects.create(
            hgnc_id="50", gene_symbol=None, alias_symbols=None
        )

        self.hgnc_release = HgncRelease.objects.create(
            hgnc_release="hgnc_v1"
        )

        self.user = "test_user"

    def test_no_changes(self):
        """
        A gene is unchanged
        """
        test_aliases = {"14163": "DKFZP761D0211,FLJ32603"}
        _update_existing_gene_metadata_aliases_in_db(test_aliases, self.hgnc_release,
                                                     self.user)

        # check that the entry isn't changed from how it was at set-up
        gene_db = Gene.objects.filter(hgnc_id="14163")
        assert len(gene_db) == 1
        assert gene_db[0].hgnc_id == self.FAM234A.hgnc_id
        assert gene_db[0].gene_symbol == self.FAM234A.gene_symbol
        assert gene_db[0].alias_symbols == self.FAM234A.alias_symbols

    def test_alias_name_change(self):
        """
        Test case: the alias name has changed for a gene, since last update
        No change in approved name
        """
        test_hgnc_aliases = {"14163": "alias1,alias2"}

        _update_existing_gene_metadata_aliases_in_db(test_hgnc_aliases, self.hgnc_release,
                                                     self.user)

        # check that the entry for 14163 in the Gene test datatable is updated
        gene_db = Gene.objects.filter(hgnc_id="14163")
        assert len(gene_db) == 1
        assert gene_db[0].alias_symbols == "alias1,alias2"
