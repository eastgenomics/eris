from unittest import mock, expectedFailure
from django.test import TestCase
from django.db.models import QuerySet
import datetime
from django_mock_queries.query import MockSet, MockModel

from requests_app.models import \
    Panel, Gene, PanelGene, PanelGeneHistory, Confidence, ModeOfInheritance, \
    Penetrance, ModeOfPathogenicity

from requests_app.management.commands._insert_panel import \
    _insert_gene

from requests_app.management.commands.history import History
from requests_app.management.commands.panelapp import PanelClass


class TestInsertGene_NewGene(TestCase):
    """
    Tests for _insert_gene
    Situations where a new panel has already been made, 
    and it gets linked to genes that aren't already in the database
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


    def test_new_panel_linked_to_acceptable_gene(self):
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


    def test_reject_low_confidence_gene(self):
        """
        Test that panel and genes are rejected if the confidence is too low
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
                                         "confidence_level": 2},
                                         {"gene_data":
                                         {"hgnc_id": 89, 
                                         "gene_name": "medium-chain acyl-CoA dehydrogenase",
                                         "gene_symbol": "ACADM", 
                                         "alias": ["MCAD", "MCADH", "ACAD1"]},
                                         "confidence_level": 3}
                                        ],
                                regions=[]
                                )

        # run the function under test
        _insert_gene(test_panel, self.first_panel)

        # check there is a panel entry - this was in the DB already
        new_panels = Panel.objects.all()
        assert len(new_panels) == 1

        # check that the confidence < 3 gene was NOT added to the database
        # only the gene with hgnc_id 89 should be in there
        new_genes = Gene.objects.all()
        assert len(new_genes) == 1
        assert new_genes[0].hgnc_id == "89"

        # check 1 panel-gene entry, which will be for the gene with HGNC 89 
        new_panel_genes = PanelGene.objects.all()
        assert len(new_panel_genes) == 1
        assert new_panel_genes[0].panel == new_panels[0]
        assert new_panel_genes[0].gene == new_genes[0]

        # check 1 history entry
        new_history = PanelGeneHistory.objects.all()
        assert len(new_history) == 1
        assert new_history[0].panel_gene == new_panel_genes[0]


    def test_rejects_no_hgnc_id_gene(self):
        """
        Test that panel and genes are rejected if the gene doesn't have a HGNC ID
        """
        # make one of the test inputs for the function
        test_panel = PanelClass(id="1141", 
                                name="Acute rhabdomyolyosis", 
                                version="1.15", 
                                panel_source="PanelApp",
                                genes=[{"gene_data": 
                                        {"hgnc_id": None, 
                                         "gene_name": "acyl-CoA dehydrogenase family member 9",
                                         "gene_symbol": "ACAD9", 
                                         "alias": ["NPD002", "MGC14452"]},
                                         "confidence_level": 3},
                                         {"gene_data": 
                                         {"hgnc_id": 89,
                                         "gene_name": "medium-chain acyl-CoA dehydrogenase",
                                         "gene_symbol": "ACADM", 
                                         "alias": ["MCAD", "MCADH", "ACAD1"]},
                                         "confidence_level": 3}
                                        ],
                                regions=[]
                                )

        # run the function under test
        _insert_gene(test_panel, self.first_panel)

        # check there is a panel entry - this was in the DB already
        new_panels = Panel.objects.all()
        assert len(new_panels) == 1

        # check that the no-HGNC ID gene was NOT added to the database
        # only the gene with hgnc_id 89 should be in there
        new_genes = Gene.objects.all()
        assert len(new_genes) == 1
        assert new_genes[0].hgnc_id == "89"

        
        # check 1 panel-gene entry, which will be for the gene with HGNC 89 
        new_panel_genes = PanelGene.objects.all()
        assert len(new_panel_genes) == 1
        assert new_panel_genes[0].panel == new_panels[0]
        assert new_panel_genes[0].gene == new_genes[0]

        # check 1 history entry
        new_history = PanelGeneHistory.objects.all()
        assert len(new_history) == 1
        assert new_history[0].panel_gene == new_panel_genes[0]


class TestInsertGene_PreexistingGene_PreexistingPanelappPanelLink(TestCase):
    """
    Tests for _insert_gene
    Situation where a new panel version panel has been added, e.g. by PanelApp import,
    and it is linked to genes that already have a link to the old version of the panel
    (so the justification is the same)
    """
    def setUp(self) -> None:
        """
        Start condition: Make a Panel, and linked genes, which we will alter as part of testing
        _insert_gene
        """
        self.first_panel = Panel.objects.create(
            external_id="1141", \
            panel_name="Acute rhabdomyolosis", \
            panel_source="PanelApp", \
            panel_version="1.15"
        )

        self.first_gene = Gene.objects.create(
            hgnc_id="21497",
            gene_symbol="ACAD9",
            alias_symbols="NPD002,MGC14452"
        )

        self.confidence = Confidence.objects.create(
            confidence_level=3
        )

        self.moi = ModeOfInheritance.objects.create(
            mode_of_inheritance="test"
        )

        self.mop = ModeOfPathogenicity.objects.create(
            mode_of_pathogenicity="test"
        )

        self.penetrance = Penetrance.objects.create(
            penetrance="test"
        )

        self.first_link = PanelGene.objects.create(
            panel=self.first_panel,
            gene=self.first_gene,
            confidence_id=self.confidence.id,
            moi_id=self.moi.id,
            mop_id=self.mop.id,
            penetrance_id=self.penetrance.id,
            justification="PanelApp"
        )


    def test_that_unchanged_gene_is_ignored(self):
        """
        Test that for a panel-gene combination that is already in the database, 
        and not updated in the PanelApp API call, we don't change them
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
                                         "confidence_level": 3,
                                         "mode_of_inheritance": "test",
                                         "mode_of_pathogenicity": "test",
                                         "penetrance": "test"}
                                        ],
                                regions=[]
                                )

        # run the function under test
        _insert_gene(test_panel, self.first_panel)

        # check that the gene is in the database 
        # and that it is unchanged from when we first added it
        new_genes = Gene.objects.all()
        assert len(new_genes) == 1
        new_gene = new_genes[0]
        assert new_gene.id == self.first_gene.id
        assert new_gene.hgnc_id == "21497"
        assert new_gene.gene_symbol == "ACAD9"
        assert new_gene.alias_symbols == "NPD002,MGC14452"

        # check that we still have just 1 PanelGene link, which should be the one
        # we made ourselves in set-up 
        panel_genes = PanelGene.objects.all()
        assert len(panel_genes) == 1
        assert panel_genes[0].id == self.first_link.id

        # the gene will be in the database, but it will be the old record
        new_panelgene = panel_genes[0]
        confidence = Confidence.objects.filter(confidence_level=3)
        assert len(confidence) == 1
        assert new_panelgene.confidence_id == confidence[0].id

        # there should not have been a history record made,
        # because there was not a change to the gene-panel link in this upload
        panel_gene_history = PanelGeneHistory.objects.all()
        assert len(panel_gene_history) == 0



    


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