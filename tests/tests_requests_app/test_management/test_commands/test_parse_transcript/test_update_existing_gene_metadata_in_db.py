from django.test import TestCase
import numpy as np

from requests_app.models import Gene

from requests_app.management.commands._parse_transcript import \
    _update_existing_gene_metadata_in_db


class TestUpdateExistingGene(TestCase):
    """
    Test various cases on _update_existing_gene_metadata_in_db
    """
    def setUp(self) -> None:
        # Populate the Gene test database with some easy examples
        self.FAM234A = Gene.objects.create(
            hgnc_id="14163",
            gene_symbol="FAM234A",
            alias_symbols="DKFZP761D0211,FLJ32603"
        )

        Gene.objects.create(
            hgnc_id="12713",
            gene_symbol="VPS41",
            alias_symbols="HVSP41"
        )

        Gene.objects.create(
            hgnc_id="50000",
            gene_symbol="YFP1",
            alias_symbols="ABC"
        )

        Gene.objects.create(
            hgnc_id="51000",
            gene_symbol="YFP2",
            alias_symbols="ABCD,EFGH"
        )

    def test_no_changes(self):
        """
        A gene is unchanged
        """
        test_hgnc_approved = {"14163": "FAM234A"}
        test_aliases = {"14163": ["DKFZP761D0211", "FLJ32603"]}        
        _update_existing_gene_metadata_in_db(test_hgnc_approved, test_aliases)

        # check that the entry isn't changed from how it was at set-up
        gene_db = Gene.objects.filter(hgnc_id="14163")
        assert len(gene_db) == 1
        assert gene_db[0].hgnc_id == self.FAM234A.hgnc_id
        assert gene_db[0].gene_symbol == self.FAM234A.gene_symbol
        assert gene_db[0].alias_symbols == self.FAM234A.alias_symbols

    def test_approved_name_change(self):
        """
        Test case: the approved name has changed for a gene, since last update
        Aliases aren't changed here
        """
        made_up_approved_name = "FAM234A_test"
        test_hgnc_approved = {"14163": made_up_approved_name} 
        test_hgnc_aliases = {"14163": ["DKFZP761D0211", "FLJ32603"]}
        _update_existing_gene_metadata_in_db(test_hgnc_approved, test_hgnc_aliases)

        # check that the entry for 14163 in the Gene test datatable is updated
        gene_db = Gene.objects.filter(hgnc_id="14163")
        assert len(gene_db) == 1
        assert gene_db[0].gene_symbol == made_up_approved_name

    def test_approved_names_change_several(self):
        """
        Test case: the approved name has changed for several genes, since last
        update
        Aliases aren't changed here
        """
        made_up_approved_name = "FAM234A_test"
        made_up_approved_name_two = "test_nonsense"

        test_hgnc_approved = {"14163": made_up_approved_name, 
                              "12713": made_up_approved_name_two}
        test_hgnc_aliases = {"14163": ["DKFZP761D0211", "FLJ32603"],
                             "12713": ["HVSP41"]}
        _update_existing_gene_metadata_in_db(test_hgnc_approved, test_hgnc_aliases)

        # check that the entry for 14163 in the Gene test datatable is updated
        gene_db = Gene.objects.filter(hgnc_id="14163")
        assert len(gene_db) == 1
        assert gene_db[0].gene_symbol == made_up_approved_name

        gene_db = Gene.objects.filter(hgnc_id="12713")
        assert len(gene_db) == 1
        assert gene_db[0].gene_symbol == made_up_approved_name_two

    def test_alias_name_change(self):
        """
        Test case: the alias name has changed for a gene, since last update
        No change in approved name
        """
        test_hgnc_approved = {"14163": "FAM234A"} 
        made_up_aliases = ["alias1", "alias2"]
        test_hgnc_aliases = {"14163": made_up_aliases}

        _update_existing_gene_metadata_in_db(test_hgnc_approved, test_hgnc_aliases)

        # check that the entry for 14163 in the Gene test datatable is updated
        gene_db = Gene.objects.filter(hgnc_id="14163")
        assert len(gene_db) == 1
        assert gene_db[0].alias_symbols == ",".join(made_up_aliases)

    def test_alias_now_numpy_na(self):
        """
        Test case: the alias name has changed for a gene, since last update
        It is now numpy 'na' data
        Expected: the alias is skipped and the old one is kept
        """
        test_hgnc_approved = {"14163": "FAM234A"}
        made_up_aliases = [np.nan]
        test_hgnc_aliases = {"14163": made_up_aliases}

        _update_existing_gene_metadata_in_db(test_hgnc_approved, test_hgnc_aliases)

        # expect the entry for 14163 in the Gene test datatable to NOT update
        gene_db = Gene.objects.filter(hgnc_id="14163")
        assert len(gene_db) == 1
        assert gene_db[0].alias_symbols == self.FAM234A.alias_symbols
    
    def test_alias_list_empty(self):
        """
        Test case: the alias name has changed for a gene, since last update
        It is now an empty list
        Expected: the alias is skipped and the old one is kept
        """
        test_hgnc_approved = {"14163": "FAM234A"}
        made_up_aliases = []
        test_hgnc_aliases = {"14163": made_up_aliases}

        _update_existing_gene_metadata_in_db(test_hgnc_approved, test_hgnc_aliases)

        # expect the entry for 14163 in the Gene test datatable to NOT update
        gene_db = Gene.objects.filter(hgnc_id="14163")
        assert len(gene_db) == 1
        assert gene_db[0].alias_symbols == self.FAM234A.alias_symbols
