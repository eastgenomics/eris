
from typing import Any
from django.test import TestCase

from requests_app.management.commands.utils import sortable_version
from requests_app.models import (
    ClinicalIndication,
    Panel,
    ClinicalIndicationPanel,
    Gene,
    PanelGene,
    PanelGeneHistory,
    ClinicalIndicationPanelHistory,
    TestDirectoryRelease,
    CiPanelTdRelease
)
from requests_app.management.commands._insert_ci import _check_for_changed_pg_justification
from tests.tests_requests_app.test_management.test_commands.test_insert_panel.test_insert_gene import (
    len_check_wrapper,
    value_check_wrapper,
)

class TestCheckChangedPg(TestCase):
    """
    """
    #TODO: write this
    def setUp(self) -> None:
        self.panel = Panel.objects.create(

        )

        self.gene = Gene.objects.create(

        )

        self.existing_pg = PanelGene.objects.create(
            panel=self.panel,
            gene=self.gene
        )
    
    def test_thing():
        _check_for_changed_pg_justification