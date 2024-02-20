from django.test import TestCase
from unittest import mock
from unittest.mock import patch, mock_open
from datetime import date

from panels_backend.models import (
    ReferenceGenome,
    TestDirectoryRelease,
    Panel,
    SuperPanel,
    Gene,
    ClinicalIndication,
    CiPanelTdRelease,
    CiSuperpanelTdRelease
)
from panels_backend.management.commands.generate import (
    Command,
)


class TestGenerateGenepanels(TestCase):
    """
    _generate_genepanels_results is primarily a controller function,
    but we want to test for the following behaviours:
    - It gets the most recent TD from several options
    - It gets both Panel and SuperPanel data, formatted correctly
    - It sorts Panels and SuperPanels together based on first 3 cols (note R
    numbers may be imperfect)
    - It excludes specific HGNCs if provided with some
    """
    def setUp(self) -> None:
        # Need multiple TdReleases
        self.td_release_old = TestDirectoryRelease.objects.create(
            release="3",
            td_source="old source",
            config_source="config source",
            td_date="2022-01-01"
        )
        self.td_release_old = TestDirectoryRelease.objects.create(
            release="3",
            td_source="old source",
            config_source="config source",
            td_date="2022-01-01"
        )

        # Muliple panels and superpanels on that TdRelease - each has
        # links to Genes
        self.panel_1 = Panel.objects.create(
            external_id="20",
            panel_name="Test panel 1",
            panel_source="Test",
            version="4",
            test_directory=True
        )

        self.panel_2 = Panel.objects.create(
            external_id="25",
            panel_name="Test panel 2",
            panel_source="Test",
            version="6",
            test_directory=True
        )

        self.superpanel_1 = SuperPanel.objects.create(
            panel_name=,
            panel_source=,
            version=,
            test_directory=True
        )
        return None
    