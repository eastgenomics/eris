from django.test import TestCase

from requests_app.models import Panel, Gene, PanelGene
from requests_app.management.commands.generate import Command


# class TestGetRelevantPanelGenes(TestCase):
#     def setUp(self) -> None:
