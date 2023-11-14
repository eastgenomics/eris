from django.test import TestCase

from requests_app.management.commands.history import History
from requests_app.management.commands._parse_transcript import (
    _link_unchanged_genes_to_new_release,
)
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


class TestLinkMade_GeneUnchanged(TestCase):
    """
    CASE: Just emulates the case when genes are still the same in the new HGNC release
    EXPECT: Gene database entries remain the same, but new links are generated to the
    new HGNC release.
    """

    def setUp(self) -> None:
        self.user = "init_v1_user"

        self.new_hgnc_release = HgncRelease.objects.create(hgnc_release="version2")

        self.gene_1 = Gene.objects.get_or_create(
            hgnc_id="1", gene_symbol="gene one", alias_symbols=None
        )
        self.gene_2 = Gene.objects.get_or_create(
            hgnc_id="2", gene_symbol="gene two", alias_symbols=None
        )
        self.gene_3 = Gene.objects.get_or_create(
            hgnc_id="3", gene_symbol="gene three", alias_symbols=None
        )

    def test_multiple_genes_linked_to_new_release(self):
        """
        CASE: Just emulates the case when genes are still the same in the new HGNC release
        EXPECT: Gene database entries remain the same, but new links are generated to the
        new HGNC release.
        """
        errors = []

        input_hgncs = ["1", "2", "3"]

        _link_unchanged_genes_to_new_release(
            input_hgncs, self.new_hgnc_release, self.user
        )

        genes = Gene.objects.all()
        errors += len_check_wrapper(genes, "number of genes", 3)

        poss_symbols = ["gene one", "gene two", "gene three"]
        for i in range(len(poss_symbols)):
            if not genes[i].gene_symbol == poss_symbols[i]:
                errors.append(
                    f"Post run gene {genes[i].gene_symbol} not equal to {poss_symbols[i]}"
                )

        # check HGNC release logging was correctly carried out
        post_run_hgnc_release_links = GeneHgncRelease.objects.all()
        errors += len_check_wrapper(
            post_run_hgnc_release_links, "number of release links", 3
        )

        for i in range(len(post_run_hgnc_release_links)):
            errors += value_check_wrapper(
                post_run_hgnc_release_links[i].hgnc_release,
                "linked release",
                self.new_hgnc_release,
            )

        post_run_history = GeneHgncReleaseHistory.objects.all()
        errors += len_check_wrapper(post_run_history, "history objects", 3)
        for i in range(len(post_run_history)):
            errors += value_check_wrapper(
                post_run_history[i].note,
                "linked history",
                History.gene_hgnc_release_present(),
            )

        errors = "; ".join(errors)
        assert not errors, errors


class TestLinkAlreadyExists(TestCase):
    """
    CASE: Emulates the case where a gene is already linked to the currently-being-added
    release.
    EXPECT: Gene-HGNC link remains the same, and no new history information is added.
    """

    def setUp(self) -> None:
        self.user = "init_v1_user"

        self.new_hgnc_release = HgncRelease.objects.create(hgnc_release="version2")

        self.gene_1 = Gene.objects.create(
            hgnc_id="1", gene_symbol="gene one", alias_symbols=None
        )

        self.link = GeneHgncRelease.objects.create(
            gene=self.gene_1, hgnc_release=self.new_hgnc_release
        )

    def test_no_history_if_gene_already_in_hgnc(self):
        """
        CASE: Emulates the case where a gene is already linked to the currently-being-added
         release.
        EXPECT: Gene-HGNC link remains the same, and no new history information is added.
        """
        errors = []

        input_hgncs = ["1"]

        _link_unchanged_genes_to_new_release(
            input_hgncs, self.new_hgnc_release, self.user
        )

        genes = Gene.objects.all()
        errors += len_check_wrapper(genes, "number of genes", 1)

        # check HGNC release link exists
        post_run_hgnc_release_links = GeneHgncRelease.objects.all()
        errors += len_check_wrapper(
            post_run_hgnc_release_links, "number of release links", 1
        )
        errors += value_check_wrapper(
            post_run_hgnc_release_links[0].gene, "gene", self.gene_1
        )
        errors += value_check_wrapper(
            post_run_hgnc_release_links[0].hgnc_release,
            "release",
            self.new_hgnc_release,
        )

        post_run_history = GeneHgncReleaseHistory.objects.all()
        errors += len_check_wrapper(post_run_history, "history objects", 0)

        errors = "; ".join(errors)
        assert not errors, errors
