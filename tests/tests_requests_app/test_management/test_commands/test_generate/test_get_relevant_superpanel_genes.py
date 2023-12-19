from django.test import TestCase

from requests_app.models import SuperPanel, Panel, Gene, PanelGene, PanelSuperPanel
from requests_app.management.commands.generate import Command


class TestGetRelevantSuperPanelGenes(TestCase):
    def setUp(self) -> None:
        # Make some superpanels, genes, and links between them
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
        self.gene_4 = Gene.objects.create(
            hgnc_id="HGNC:300", gene_symbol="YF2", alias_symbols=None
        )

        # Make a Panel to link some genes to
        self.panel_1 = Panel.objects.create(
            external_id="",
            panel_name="Panel 1",
            panel_source="PanelApp",
            panel_version="2",
            test_directory=False,
            custom=False,
            pending=False,
        )

        # Make a second Panel to link some genes to
        self.panel_2 = Panel.objects.create(
            external_id="",
            panel_name="Panel 2",
            panel_source="PanelApp",
            panel_version="1",
            test_directory=False,
            custom=False,
            pending=False,
        )

        # only some PanelGene links are active and NOT pending
        # note that some Genes are linked to more than one Panel in a SuperPanel, which happens sometimes
        # in real life
        self.pg_1 = PanelGene.objects.create(
            panel=self.panel_1,
            gene=self.gene_1,
            moi=None,
            mop=None,
            penetrance=None,
            justification="test",
            active=True,
            pending=False,
        )
        self.pg_2 = PanelGene.objects.create(
            panel=self.panel_1,
            gene=self.gene_2,
            moi=None,
            mop=None,
            penetrance=None,
            justification="test",
            active=False,  # note not active
            pending=False,
        )
        self.pg_3 = PanelGene.objects.create(
            panel=self.panel_2,
            gene=self.gene_3,
            moi=None,
            mop=None,
            penetrance=None,
            justification="test",
            active=True,
            pending=True,  # note pending
        )
        self.pg_4 = PanelGene.objects.create(
            panel=self.panel_2,
            gene=self.gene_4,
            moi=None,
            mop=None,
            penetrance=None,
            justification="test",
            active=True,
            pending=False,
        )
        self.pg_5 = PanelGene.objects.create(
            panel=self.panel_2,
            gene=self.gene_1,  # gene 1 is present in BOTH Panels
            moi=None,
            mop=None,
            penetrance=None,
            justification="test",
            active=True,
            pending=False,
        )

        # finally, we have a SuperPanel with two Panels connected to it
        self.superpanel = SuperPanel.objects.create(
            external_id="",
            panel_name="Super Panel",
            panel_source="PanelApp",
            panel_version="5",
            test_directory=False,
            custom=False,
            pending=False,
        )

        self.psp_1 = PanelSuperPanel.objects.create(
            panel=self.panel_1, superpanel=self.superpanel
        )

        self.psp_2 = PanelSuperPanel.objects.create(
            panel=self.panel_2, superpanel=self.superpanel
        )

    def test_only_active_nonpending_genes_retrieved(self):
        """
        CASE: We want to fetch genes linked to a SuperPanel. Some genes are active and not-pending,
        some are in other states.
        EXPECT: We only retrieve the active, not-pending genes that are linked to the child-Panels
        of this SuperPanel. The other genes are skipped.
        """
        cmd = Command()

        expected_superpanel_genes = {self.superpanel.id: set(["HGNC:910", "HGNC:300"])}

        actual_superpanel_genes = cmd._get_relevant_superpanel_genes(
            [self.superpanel.pk]
        )

        self.assertDictEqual(expected_superpanel_genes, actual_superpanel_genes)
