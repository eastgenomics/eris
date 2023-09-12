from unittest import mock, expectedFailure
from django.test import TestCase
from django.db.models import QuerySet
import datetime
from django_mock_queries.query import MockSet, MockModel

from requests_app.models import \
    Panel, Gene, PanelGene, PanelGeneHistory, Confidence, ModeOfInheritance, \
    Penetrance, ModeOfPathogenicity

from requests_app.management.commands._insert_panel import \
    _backward_deactivate_panel_gene

from requests_app.management.commands.history import History
from requests_app.management.commands.panelapp import PanelClass

# TODO: '_backward_deactivate_panel_gene' requires fixing before testing 
# (it sets PanelGene to 'pending' but this isn't in models)

# class TestBackwardsDeactivatePanelGene_SingleGene(TestCase):
#     def setUp(self) -> None:
#         """
#         Set up a Panel, one Gene, and their PanelGene link
#         """
#         self.first_panel = Panel.objects.create(
#             external_id="1141", \
#             panel_name="Acute rhabdomyolosis", \
#             panel_source="PanelApp", \
#             panel_version="1.15"
#         )

#         self.first_gene = Gene.objects.create(
#             hgnc_id=21497,
#             gene_symbol="ACAD9",
#             alias_symbols="NPD002, MGC14452"
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



#     def test_deactivate_single_gene(self):
#         """
#         Checking the most basic case - a single gene needs reviewing for whether it should 
#          be removed from the panel
#         """
#         panel_class = PanelClass(id="1141", 
#                                 name="Acute rhabdomyolyosis", 
#                                 version="1.15", 
#                                 panel_source="PanelApp",
#                                 genes=[{"gene_data": 
#                                         {"hgnc_id": 21497, 
#                                          "gene_name": "acyl-CoA dehydrogenase family member 9",
#                                          "gene_symbol": "ACAD9", 
#                                          "alias": ["NPD002", "MGC14452"]},
#                                          "confidence_level": 3}
#                                         ],
#                                 regions=[]
#                                 )
#         panel_db = Panel.objects.all()
#         assert len(panel_db) == 1
#         panel_db = panel_db[0]

#         # assert gene-panel link is NOT pending before we run the command
#         panel_gene = PanelGene.objects.all()
#         assert len(panel_gene) == 1
#         assert panel_gene[0].pending == False

#         # run command
#         _backward_deactivate_panel_gene(panel_class, panel_db)

#         # check for genes, there should be 1
#         genes = Gene.objects.all()
#         assert len(genes) == 1
    
#         # check the gene-panel link is PENDING
#         panel_gene = PanelGene.objects.all()
#         assert len(panel_gene) == 1
#         assert panel_gene[0].pending == True

