from django.test import TestCase

from requests_app.management.commands._parse_transcript import _add_new_genes_to_db
from tests.tests_requests_app.test_management.test_commands.test_insert_ci.test_insert_test_directory_data import (
    len_check_wrapper,
)
from requests_app.models import Gene


class TestGetOrCreate_CreateNew(TestCase):
    """
    Just emulates straightforward entry of new genes
    EXPECT: single entry in the database for each gene
    """

    def setUp(self) -> None:
        pass

    def test_adding_identical_gene(self):
        errors = []

        approved_symbols = {"HGNC:10257": "ROR2", "HGNC:TEST": "TEST_SYMBOL"}
        alias_symbols = {"HGNC:10257": None, "HGNC:TEST": "TEST, ALIAS"}

        _add_new_genes_to_db(approved_symbols, alias_symbols)

        post_run_genes = Gene.objects.all()
        errors += len_check_wrapper(post_run_genes, "number of post run genes", 2)

        poss_symbols = ["ROR2", "TEST_SYMBOL"]
        poss_aliases = [None, "TEST, ALIAS"]
        for i in range(0, 2, 1):
            if not post_run_genes[i].gene_symbol in poss_symbols:
                errors.append(
                    f"Post run gene {post_run_genes[i].gene_symbol} not in {poss_symbols}"
                )
            if not post_run_genes[i].alias_symbols in poss_aliases:
                errors.append(
                    f"Post run gene {post_run_genes[i].alias_symbols} not in {poss_aliases}"
                )

        errors = "; ".join(errors)
        assert not errors, errors
