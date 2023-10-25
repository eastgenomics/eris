from django.test import TestCase

from unittest import mock
import pandas as pd


from requests_app.management.commands._parse_transcript import _add_new_genes_to_db
from requests_app.models import Gene

#TODO: change these tests
class TestGetOrCreate_AlreadyExistsIdentical(TestCase):
    """
    A test built because I didn't understand the behaviour of get_or_create/
    update_or_create.
    Emulates a case where a gene/transcript are entered twice, 
    exactly the same
    EXPECT: single entry in the database for the gene
    """
    def setUp(self) -> None:
        self.gene = Gene.objects.create(hgnc_id="HGNC:10257",
                                        gene_symbol="ROR2",
                                        alias_symbols=None)
        
    def test_adding_identical_gene(self):
        input_hgnc = "HGNC:10257"
        matches = [{'HGNC ID': 'HGNC:10257', 'Approved symbol': 'ROR2', 'Alias symbols': None}]
        result = _add_new_genes_to_db(input_hgnc, matches)
        assert result == self.gene


class TestGetOrCreate_AlreadyExistsSlightlyDifferent(TestCase):
    """
    A test built because I didn't understand the behaviour of get_or_create/
    update_or_create.
    Emulates a case where a gene/transcript are entered twice, 
    once with less info, a second time with more info
    """
    def setUp(self) -> None:
        self.gene = Gene.objects.create(hgnc_id="HGNC:10257",
                                        gene_symbol=None,
                                        alias_symbols=None)
        
    def test_adding_identical_gene(self):
        input_hgnc = "HGNC:10257"
        matches = [{'HGNC ID': 'HGNC:10257', 'Approved symbol': "TEST", 'Alias symbols': "TEST, ALIAS"}]
        _ = _add_new_genes_to_db(input_hgnc, matches)
        
        # check the entry updates in db
        results = Gene.objects.all()
        assert len(results) == 1
        assert results[0].hgnc_id == "HGNC:10257"
        assert results[0].gene_symbol == "TEST"
        assert results[0].alias_symbols == "TEST, ALIAS"
