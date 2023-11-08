from django.test import TestCase
import numpy as np

from requests_app.models import Gene, HgncRelease, GeneHgncRelease, GeneHgncReleaseHistory

from requests_app.management.commands.history import History
from requests_app.management.commands._parse_transcript import (
    _update_existing_gene_metadata_symbol_in_db,
    _update_existing_gene_metadata_aliases_in_db,
)
from tests.tests_requests_app.test_management.test_commands.test_insert_panel.test_insert_gene import (
    len_check_wrapper,
    value_check_wrapper,
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

    def test_approved_name_change(self):
        """
        Test case: the approved name has changed for a gene, since last update
        """
        err = []

        made_up_approved_name = "FAM234A_test"
        test_hgnc_approved = {"14163": made_up_approved_name}
        _update_existing_gene_metadata_symbol_in_db(test_hgnc_approved, self.hgnc_release,
                                                    self.user)

        # check that the entry for 14163 in the Gene test datatable is updated
        gene_db = Gene.objects.filter(hgnc_id="14163")
        err += len_check_wrapper(gene_db, "gene objects matching 14163", 1)
        err += value_check_wrapper(gene_db[0].gene_symbol, "gene symbol", made_up_approved_name)

        # check that the entry has been linked to a HgncRelease
        gene_release = GeneHgncRelease.objects.all()
        err += len_check_wrapper(gene_release, "Gene-HGNC links", 1)
        err += value_check_wrapper(gene_release[0].gene, "gene in the link", gene_db[0])

        # and there's a HgncRelease history entry with the 'symbol change' message
        history = GeneHgncReleaseHistory.objects.all()
        err += len_check_wrapper(history, "history entries", 1)
        err += value_check_wrapper(history[0].gene_hgnc_release, "Gene-HGNC link", gene_release[0])
        err += value_check_wrapper(history[0].note, "history note",
                                   History.gene_hgnc_release_approved_symbol_change())

        errors = "; ".join(err)
        assert not errors, errors

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

        err = []

        # check that the entry for 14163 in the Gene test datatable is updated
        gene_db_one = Gene.objects.filter(hgnc_id="14163")
        err += len_check_wrapper(gene_db_one, "genes matching 14163", 1)
        err += value_check_wrapper(gene_db_one[0].gene_symbol, "gene symbol", made_up_approved_name)

        gene_db_two = Gene.objects.filter(hgnc_id="12713")
        err += len_check_wrapper(gene_db_two, "genes matching 12713", 1)
        err += value_check_wrapper(gene_db_two[0].gene_symbol, "gene symbol", made_up_approved_name_two)

        # check that the two gene entries have been linked to a HgncRelease
        gene_release = GeneHgncRelease.objects.all()
        err += len_check_wrapper(gene_release, "Gene-HGNC links", 2)
        err += value_check_wrapper(gene_release[0].gene, "gene in the link", gene_db_one[0])
        err += value_check_wrapper(gene_release[1].gene, "gene in the link", gene_db_two[0])

        # and there's a HgncRelease history entry with the 'symbol change' message
        history = GeneHgncReleaseHistory.objects.all()
        err += len_check_wrapper(history, "history", 2)
        err += value_check_wrapper(history[0].gene_hgnc_release, "Gene-HGNC link", gene_release[0])
        err += value_check_wrapper(history[0].note, "history note",
                                   History.gene_hgnc_release_approved_symbol_change())
        err += value_check_wrapper(history[1].gene_hgnc_release, "Gene-HGNC link", gene_release[1])
        err += value_check_wrapper(history[1].note, "history note",
                                   History.gene_hgnc_release_approved_symbol_change())

        errors = "; ".join(err)
        assert not errors, errors

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

    def test_alias_name_change(self):
        """
        Test case: the alias name has changed for a gene, since last update
        No change in approved name
        """
        test_hgnc_aliases = {"14163": "alias1,alias2"}

        _update_existing_gene_metadata_aliases_in_db(test_hgnc_aliases, self.hgnc_release,
                                                     self.user)

        err = []

        # check that the entry for 14163 in the Gene test datatable is updated
        gene_db = Gene.objects.filter(hgnc_id="14163")
        err += len_check_wrapper(gene_db, "genes", 1)
        err += value_check_wrapper(gene_db[0].alias_symbols, "alias symbol", "alias1,alias2")

        # check that the entry has been linked to a HgncRelease
        gene_release = GeneHgncRelease.objects.all()
        err += len_check_wrapper(gene_release, "Gene-HGNC links", 1)
        err += value_check_wrapper(gene_release[0].gene, "gene in the link", gene_db[0])

        # and there's a HgncRelease history entry with the 'symbol change' message
        history = GeneHgncReleaseHistory.objects.all()
        err += len_check_wrapper(history, "history entries", 1)
        err += value_check_wrapper(history[0].gene_hgnc_release, "Gene-HGNC link", gene_release[0])
        err += value_check_wrapper(history[0].note, "history note",
                                   History.gene_hgnc_release_alias_symbol_change())

        errors = "; ".join(err)
        assert not errors, errors