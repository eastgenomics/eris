from django.test import TestCase

from requests_app.models import Panel, Gene, PanelGene
from requests_app.management.commands.generate import Command


class TestGetRelevantPanelGenes(TestCase):
    def setUp(self) -> None:
        # Make some panels, genes, and links between them
        # Some are not active, some are active
        self.gene_1 = Gene.objects.create(
            hgnc_id="HGNC:910", gene_symbol="YFG1", alias_symbols="YFG,ETC"
        )
        self.gene_2 = Gene.objects.create(
            hgnc_id="HGNC:911", gene_symbol="YFG2", alias_symbols="YFG"
        )
        self.gene_3 = Gene.objects.create(
            hgnc_id="HGNC:912", gene_symbol="YFG3", alias_symbols=None
        )

        self.panel = Panel.objects.create(
            external_id="",
            panel_name="",
            panel_source="PanelApp",
            panel_version="5",
            test_directory=False,
            custom=False,
            pending=False,
        )

        # only some PanelGene links are active and NOT pending - one is not Active, one is Pending
        self.pg_1 = PanelGene.objects.create(
            panel=self.panel,
            gene=self.gene_1,
            moi=None,
            mop=None,
            penetrance=None,
            justification="test",
            active=True,
            pending=False,
        )
        self.pg_2 = PanelGene.objects.create(
            panel=self.panel,
            gene=self.gene_2,
            moi=None,
            mop=None,
            penetrance=None,
            justification="test",
            active=False,  # note not active
            pending=False,
        )
        self.pg_3 = PanelGene.objects.create(
            panel=self.panel,
            gene=self.gene_3,
            moi=None,
            mop=None,
            penetrance=None,
            justification="test",
            active=True,
            pending=True,  # note pending
        )

    def test_only_active_nonpending_genes_retrieved(self):
        """
        CASE: We want to fetch genes linked to a Panel. Some are active and not-pending, some are in other states.
        EXPECT: We only retrieve the active, not-pending gene that is linked to the Panel. The other genes are skipped.
        """
        cmd = Command()

        expected_panel_genes = {self.panel.id: ["HGNC:910"]}

        actual_panel_genes = cmd._get_relevant_panel_genes([self.panel.pk])

        self.assertDictEqual(expected_panel_genes, actual_panel_genes)
