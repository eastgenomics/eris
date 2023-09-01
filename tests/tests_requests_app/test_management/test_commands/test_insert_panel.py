from unittest import mock, expectedFailure
from django.test import TestCase
from django.db.models import QuerySet
import datetime
from django_mock_queries.query import MockSet, MockModel

from requests_app.models import \
    Panel, Gene, PanelGene, PanelGeneHistory, Confidence

from requests_app.management.commands._insert_panel import \
    _insert_gene

from requests_app.management.commands.history import History
from requests_app.management.commands.panelapp import PanelClass


class TestInsertGene_NewGene(TestCase):
    """
    Tests for _insert_gene
    Situation where a new panel has already been made, 
    and it is linked to genes that aren't already in the database
    """
    def setUp(self) -> None:
        """
        Start condition: Make a Panel, which we will link to genes as part of testing
        _insert_gene
        """
        self.first_panel = Panel.objects.create(
            external_id="1141", \
            panel_name="Acute rhabdomyolosis", \
            panel_source="PanelApp", \
            panel_version="1.15"
        )


    def test_new_panel_and_genes_linked(self):
        """
        Test that panel and genes are created,
        then linked, and their history logged
        """
        # make one of the test inputs for the function
        test_panel = PanelClass(id="1141", 
                                name="Acute rhabdomyolyosis", 
                                version="1.15", 
                                panel_source="PanelApp",
                                genes=[{"gene_data": 
                                        {"hgnc_id": 21497, 
                                         "gene_name": "acyl-CoA dehydrogenase family member 9",
                                         "gene_symbol": "ACAD9", 
                                         "alias": ["NPD002", "MGC14452"]},
                                         "confidence_level": 3}
                                        ],
                                regions=[]
                                )

        # run the function under test
        _insert_gene(test_panel, self.first_panel)

        # check that the gene was added to the database
        new_genes = Gene.objects.all()
        assert len(new_genes) == 1
        new_gene = new_genes[0]
        assert new_gene.hgnc_id == "21497"
        assert new_gene.gene_symbol == "ACAD9"
        assert new_gene.alias_symbols == "NPD002,MGC14452"

        # check that the gene was linked to the panel
        # with the correct confidence level
        panel_genes = PanelGene.objects.filter(panel=self.first_panel.id, gene=new_gene.id)
        assert len(panel_genes) == 1
        new_panelgene = panel_genes[0]
        confidence = Confidence.objects.filter(confidence_level=3)
        assert len(confidence) == 1
        assert new_panelgene.confidence_id == confidence[0].id

        # check a history record was made for a NEW link
        panel_gene_history = PanelGeneHistory.objects.filter(panel_gene=new_panelgene.id)
        assert len(panel_gene_history) == 1
        new_history = panel_gene_history[0]
        assert new_history.note == History.panel_gene_created()
        assert new_history.user == "PanelApp"








### Check confidence-catching, and HGNC ID catching

### Possible conditions:
# Gene can be NOT IN THE DB ALREADY, or OLD
# Gene can be ALREADY LINKED TO THE PANEL or NOT


## Cases and expectations:
## New panel, gene which isn't in Gene table yet
    # Gene added to Gene table, and linked to PanelGene. PanelGeneHistory is updated.
## New panel, gene which IS in Gene table (from some other panel?)
## New panel, gene with CI level 2

## Old panel, gene which isn't in Gene table yet
## Old panel, gene which IS in Gene table
## Old panel, gene with CI level 2


# New panel, new confident gene, not linked yet
# New panel, old confident gene, not linked yet


# Impossible combinations:
# Old gene with NON-LEVEL-3 confidence