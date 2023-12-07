from django.test import TestCase

from requests_app.management.commands.history import History
from requests_app.management.commands._parse_transcript import _add_new_genes_to_db
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


class TestGetOrCreate_CreateNew(TestCase):
    """
    CASE: Just emulates straightforward entry of new genes
    EXPECT: single entry in the database for each gene
    """

    def setUp(self) -> None:
        self.hgnc_release = HgncRelease.objects.create(hgnc_release="new_hgnc")
        self.user = "init_v1_user"

    def test_adding_new_gene(self):
        errors = []

        input = [
            {"hgnc_id": "HGNC:10257", "symbol": "ROR2", "alias": None},
            {"hgnc_id": "HGNC:TEST", "symbol": "TEST_SYMBOL", "alias": "TEST, ALIAS"},
        ]

        _add_new_genes_to_db(input, self.hgnc_release, self.user)

        post_run_genes = Gene.objects.all()
        errors += len_check_wrapper(post_run_genes, "number of post run genes", 2)

        poss_symbols = ["ROR2", "TEST_SYMBOL"]
        poss_aliases = [None, "TEST, ALIAS"]
        for i in range(0, 2, 1):
            if post_run_genes[i].gene_symbol not in poss_symbols:
                errors.append(
                    f"Post run gene {post_run_genes[i].gene_symbol} not in {poss_symbols}"
                )
            if post_run_genes[i].alias_symbols not in poss_aliases:
                errors.append(
                    f"Post run gene {post_run_genes[i].alias_symbols} not in {poss_aliases}"
                )

        # check HGNC release logging was correctly carried out
        post_run_hgnc_release_links = GeneHgncRelease.objects.all()
        errors += len_check_wrapper(
            post_run_hgnc_release_links, "number of release links", 2
        )

        for i in range(len(post_run_hgnc_release_links)):
            errors += value_check_wrapper(
                post_run_hgnc_release_links[i].hgnc_release,
                "linked release",
                self.hgnc_release,
            )

        post_run_history = GeneHgncReleaseHistory.objects.all()
        errors += len_check_wrapper(post_run_history, "number of history entries", 2)

        for i in range(len(post_run_history)):
            errors += value_check_wrapper(
                post_run_history[i].note,
                "linked history",
                History.gene_hgnc_release_new(),
            )

        errors = "; ".join(errors)
        assert not errors, errors
