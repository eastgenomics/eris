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


# Impossible combinations:
# Old gene version in database with NON-LEVEL-3 confidence
# Old gene version in database without a HGNC number


def len_check_wrapper(metric, metric_name, expected) -> str | list:
    """
    Checks that length of a list of metrics matches the expected length.
    Returns an error if not, otherwise returns an empty list.
    Saves a line of code every time I have to check that a data table 
    contains the expected number of entries.
    """
    if len(metric) != expected:
        msg = (f"The number of {metric_name} entries in the database is {len(metric)} "
            f"which does not match the expected: {expected}")
        return msg
    else:
        return [] # empty list


def value_check_wrapper(metric, metric_name, expected) -> str | list:
    """
    Checks that value of a metric matches the expected value.
    Returns an error if not, otherwise returns an empty list.
    Saves formatting the error message constantly.
    """
    if metric != expected:
        msg = (f"The value of {metric_name} is {metric} which does not match the expected: {expected}")
        return msg
    else:
        return []
    
class TestInsertGene_NewGene(TestCase):
    """
    Tests for _insert_gene
    Situations where a new panel has already been made, 
    and it gets linked to genes that aren't already in the database
    """

    #errors = []

    def setUp(self) -> None:
        """
        Start condition: Make a Panel, which we will link to genes as part of testing
        _insert_gene
        """
        self.first_panel = Panel.objects.create(
            external_id="1141", 
            panel_name="Acute rhabdomyolosis", 
            panel_source="PanelApp", 
            panel_version="1.15"
        )


    def test_new_panel_linked_to_acceptable_gene(self):
        """
        Test that panel and genes are created,
        then linked, and their history logged
        """
        # make one of the test inputs for the function
        errors = []

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
        errors += len_check_wrapper(new_genes, "gene", 1)
        
        new_gene = new_genes[0]
        errors += value_check_wrapper(new_gene.hgnc_id, "gene's HGNC ID", "21497")
        errors += value_check_wrapper(new_gene.gene_symbol, "gene's symbol", "ACAD9")
        errors += value_check_wrapper(new_gene.alias_symbols, "alias symbols", "NPD002,MGC14452")

        # check that the gene was linked to the panel
        # with the correct confidence level
        panel_genes = PanelGene.objects.filter(panel=self.first_panel.id, gene=new_gene.id)
        errors += len_check_wrapper(panel_genes, "panel-genes", 1)
        new_panelgene = panel_genes[0]
        confidence = Confidence.objects.filter(confidence_level=3)
        errors += len_check_wrapper(confidence, "confidence", 1)
        errors += value_check_wrapper(new_panelgene.confidence_id, "confidence ID", 1)

        # check a history record was made for a NEW link
        panel_gene_history = PanelGeneHistory.objects.filter(panel_gene=new_panelgene.id)
        errors += len_check_wrapper(panel_gene_history, "panel-gene history", 1)
        new_history = panel_gene_history[0]
        if not new_history.note == History.panel_gene_created():
            errors.append(f"The History entry from the datatable, "
                          f"does not have a 'panel gene created' note: {new_history.note}")
        if not new_history.user == "PanelApp":
            errors.append(f"The History entry from the datatable, "
                          f"does not have the user set as PanelApp: {new_history.user}")
        
        errors = "".join(errors)
        assert not errors, errors


    def test_reject_low_confidence_gene(self):
        """
        Test that panel and genes are rejected if the confidence is too low
        """
        errors = []

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
        errors += len_check_wrapper(new_panels, "panels", 1)
        # check that the confidence < 3 gene was NOT added to the database
        # only the gene with hgnc_id 89 should be in there
        new_genes = Gene.objects.all()
        errors += len_check_wrapper(new_genes, "genes", 1)
        errors += value_check_wrapper(new_genes[0].hgnc_id, "gene HGNC ID", "89")
        
        # check 1 panel-gene entry, which will be for the gene with HGNC 89 
        new_panel_genes = PanelGene.objects.all()
        errors += len_check_wrapper(new_panel_genes, "panel-genes", 1)
        if not new_panel_genes[0].panel == new_panels[0]:
            errors.append(f"PanelGene entry does not match our expected Panel: {new_panel_genes.panel}")

            
        if not new_panel_genes[0].gene == new_genes[0]:
            errors.append(f"PanelGene entry does not match our expected Gene: {new_panel_genes.gene}")

        # check 1 history entry
        new_history = PanelGeneHistory.objects.all()
        errors += len_check_wrapper(new_history, "panel-gene history", 1)
        if not new_history[0].panel_gene == new_panel_genes[0]:
            errors.append(f"History entry does not match our expected PanelGene: {new_history[0].panel_gene}")

        errors = "".join(errors)
        assert not errors, errors


    def test_rejects_no_hgnc_id_gene(self):
        """
        Test that panel and genes are rejected if the gene doesn't have a HGNC ID
        """
        errors = []
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
        errors += len_check_wrapper(new_panels, "panel", 1)

        # check that the no-HGNC ID gene was NOT added to the database
        # only the gene with hgnc_id 89 should be in there
        new_genes = Gene.objects.all()
        errors += len_check_wrapper(new_genes, "genes", 1)
        errors += value_check_wrapper(new_genes[0].hgnc_id, "gene HGNC ID", "89")
        
        # check 1 panel-gene entry, which will be for the gene with HGNC 89 
        new_panel_genes = PanelGene.objects.all()
        errors += len_check_wrapper(new_panel_genes, "panel-genes", 1)
        errors += value_check_wrapper(new_panel_genes[0].panel, "panel-gene link panel", new_panels[0])
        errors += value_check_wrapper(new_panel_genes[0].gene, "panel-gene link panel", new_genes[0])

        # check 1 history entry
        new_history = PanelGeneHistory.objects.all()
        errors += len_check_wrapper(new_history, "panel-gene history", 1)
        errors += value_check_wrapper(new_history[0].panel_gene, "panel-gene history's panel gene link", 
                                      new_panel_genes[0])

        errors = "".join(errors)
        assert not errors, errors


# class TestInsertGene_PreexistingGene_PreexistingPanelappPanelLink(TestCase):
#     """
#     Tests for _insert_gene
#     Situation where a panel has already been previously added, e.g. by PanelApp import,
#     so that is is already present with the correct gene links
#     """
#     def setUp(self) -> None:
#         """
#         Start condition: Make a Panel, and linked genes
#         """
#         self.first_panel = Panel.objects.create(
#             external_id="1141", 
#             panel_name="Acute rhabdomyolosis", 
#             panel_source="PanelApp", 
#             panel_version="1.15"
#         )

#         self.first_gene = Gene.objects.create(
#             hgnc_id="21497",
#             gene_symbol="ACAD9",
#             alias_symbols="NPD002,MGC14452"
#         )

#         self.confidence = Confidence.objects.create(
#             confidence_level=3
#         )

#         self.moi = ModeOfInheritance.objects.create(
#             mode_of_inheritance="test"
#         )

#         self.mop = ModeOfPathogenicity.objects.create(
#             mode_of_pathogenicity="test"
#         )

#         self.penetrance = Penetrance.objects.create(
#             penetrance="test"
#         )

#         self.first_link = PanelGene.objects.create(
#             panel=self.first_panel,
#             gene=self.first_gene,
#             confidence_id=self.confidence.id,
#             moi_id=self.moi.id,
#             mop_id=self.mop.id,
#             penetrance_id=self.penetrance.id,
#             justification="PanelApp"
#         )


#     def test_that_unchanged_gene_is_ignored(self):
#         """
#         Test that for a panel-gene combination that is already in the database, 
#         and not updated in the PanelApp API call, we don't change them
#         """
#         errors = []

#         # make one of the test inputs for the function
#         test_panel = PanelClass(id="1141", 
#                                 name="Acute rhabdomyolyosis", 
#                                 version="1.15", 
#                                 panel_source="PanelApp",
#                                 genes=[{"gene_data": 
#                                         {"hgnc_id": 21497, 
#                                          "gene_name": "acyl-CoA dehydrogenase family member 9",
#                                          "gene_symbol": "ACAD9", 
#                                          "alias": ["NPD002", "MGC14452"]},
#                                          "confidence_level": 3,
#                                          "mode_of_inheritance": "test",
#                                          "mode_of_pathogenicity": "test",
#                                          "penetrance": "test"}
#                                         ],
#                                 regions=[]
#                                 )

#         # run the function under test
#         _insert_gene(test_panel, self.first_panel)

#         # check that the gene is in the database 
#         # and that it is unchanged from when we first added it
#         new_genes = Gene.objects.all()
#         if not len(new_genes) == 1:
#             errors.append(f"Number of new genes in the datatable does not equal 1: {len(new_genes)}")
#         new_gene = new_genes[0]
#         assert new_gene.id == self.first_gene.id
#         assert new_gene.hgnc_id == "21497"
#         assert new_gene.gene_symbol == "ACAD9"
#         assert new_gene.alias_symbols == "NPD002,MGC14452"

#         # check that we still have just 1 PanelGene link, which should be the one
#         # we made ourselves in set-up 
#         panel_genes = PanelGene.objects.all()
#         assert len(panel_genes) == 1
#         assert panel_genes[0].id == self.first_link.id

#         # the gene will be in the database, but it will be the old record
#         new_panelgene = panel_genes[0]
#         confidence = Confidence.objects.filter(confidence_level=3)
#         assert len(confidence) == 1
#         assert new_panelgene.confidence_id == confidence[0].id

#         # there should not have been a history record made,
#         # because there was not a change to the gene-panel link in this upload
#         panel_gene_history = PanelGeneHistory.objects.all()
#         assert len(panel_gene_history) == 0


# class TestInsertGene_PreexistingGene_MultiplePanelVersions(TestCase):
#     """
#     Tests for _insert_gene
#     Situation where a new version panel has been added, e.g. by PanelApp import,
#     and it is linked to genes that already have a link to the old version of the panel
#     (so the justification is the same)
#     """
#     def setUp(self) -> None:
#         """
#         Start condition: Make two versions of a Panel, the old one already has a linked gene
#         The new version won't be linked until _insert_gene runs
#         """
#         self.first_panel = Panel.objects.create(
#             external_id="1141", 
#             panel_name="Acute rhabdomyolosis", 
#             panel_source="PanelApp", 
#             panel_version="1.15"
#         )

#         self.second_panel = Panel.objects.create(
#             external_id="1141", 
#             panel_name="Acute rhabdomyolosis", 
#             panel_source="PanelApp", 
#             panel_version="1.16" # note different version
#         )

#         self.first_gene = Gene.objects.create(
#             hgnc_id="21497",
#             gene_symbol="ACAD9",
#             alias_symbols="NPD002,MGC14452"
#         )

#         self.confidence = Confidence.objects.create(
#             confidence_level=3
#         )

#         self.moi = ModeOfInheritance.objects.create(
#             mode_of_inheritance="test"
#         )

#         self.mop = ModeOfPathogenicity.objects.create(
#             mode_of_pathogenicity="test"
#         )

#         self.penetrance = Penetrance.objects.create(
#             penetrance="test"
#         )

#         self.first_link = PanelGene.objects.create(
#             panel=self.first_panel,
#             gene=self.first_gene,
#             confidence_id=self.confidence.id,
#             moi_id=self.moi.id,
#             mop_id=self.mop.id,
#             penetrance_id=self.penetrance.id,
#             justification="PanelApp"
#         )


#     def test_that_gene_in_db_linked_to_new_panel_version(self):
#         """
#         Test that when the PanelApp API call has a NEW VERSION of a panel,
#         and the old and new versions are both in the database, 
#          the gene is successfully linked to the new panel
#         """
#         # make one of the test inputs for the function        
#         test_panel = PanelClass(id="1141", 
#                                 name="Acute rhabdomyolyosis", 
#                                 version="1.16", #note version change 
#                                 panel_source="PanelApp",
#                                 genes=[{"gene_data": 
#                                         {"hgnc_id": 21497, 
#                                          "gene_name": "acyl-CoA dehydrogenase family member 9",
#                                          "gene_symbol": "ACAD9", 
#                                          "alias": ["NPD002", "MGC14452"]},
#                                          "confidence_level": 3,
#                                          "mode_of_inheritance": "test",
#                                          "mode_of_pathogenicity": "test",
#                                          "penetrance": "test"}
#                                         ],
#                                 regions=[]
#                                 )

#         # run the function under test
#         _insert_gene(test_panel, self.second_panel)

#         # check that the gene is in the database 
#         # and that it is unchanged from when we first added it
#         all_genes = Gene.objects.all()
#         assert len(all_genes) == 1
#         new_gene = all_genes[0]
#         assert new_gene.id == self.first_gene.id
#         assert new_gene.hgnc_id == "21497"
#         assert new_gene.gene_symbol == "ACAD9"
#         assert new_gene.alias_symbols == "NPD002,MGC14452"

#         # check that we now have 2 PanelGene links, one which we made ourselves in set-up,
#         # one which is made now as a panel version increases
#         panel_genes = PanelGene.objects.all()
#         assert len(panel_genes) == 2
#         assert panel_genes[0].id == self.first_link.id
#         assert panel_genes[1].panel == self.second_panel


#         # History record should link the old gene to the new panel version
#         panel_gene_history = PanelGeneHistory.objects.all()
#         assert len(panel_gene_history) == 1
#         assert panel_gene_history[0].panel_gene == panel_genes[1]

