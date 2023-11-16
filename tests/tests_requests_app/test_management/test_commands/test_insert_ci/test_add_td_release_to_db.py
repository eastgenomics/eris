
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
from requests_app.management.commands._insert_ci import _add_td_release_to_db
from tests.tests_requests_app.test_management.test_commands.test_insert_panel.test_insert_gene import (
    len_check_wrapper,
    value_check_wrapper,
)

#TODO: write tests here