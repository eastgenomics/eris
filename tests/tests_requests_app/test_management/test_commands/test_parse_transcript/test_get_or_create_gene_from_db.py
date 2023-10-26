from django.test import TestCase

from unittest import mock
import pandas as pd
from django.db import transaction

from requests_app.management.commands._parse_transcript import _add_new_genes_to_db
from requests_app.models import Gene

class TestGetOrCreate_CreateNew(TestCase):
    """
    Just emulates straightforward entry of new genes
    EXPECT: single entry in the database for each gene
    """
    def setUp(self) -> None:
        pass
        
    def test_adding_identical_gene(self):
        approved_symbols = {"HGNC:10257": "ROR2", "HGNC:TEST": "TEST_SYMBOL"}
        alias_symbols = {"HGNC:10257": None, "HGNC:TEST": "TEST, ALIAS"}

        _add_new_genes_to_db(approved_symbols, alias_symbols)

        post_run_genes = Gene.objects.all()
        assert len(post_run_genes) == 2
        assert post_run_genes[0].gene_symbol in ["ROR2", "TEST_SYMBOL"]
        assert post_run_genes[1].gene_symbol in ["ROR2", "TEST_SYMBOL"]
        assert post_run_genes[0].alias_symbols in [None, "TEST, ALIAS"]
        assert post_run_genes[1].alias_symbols in [None, "TEST, ALIAS"]
