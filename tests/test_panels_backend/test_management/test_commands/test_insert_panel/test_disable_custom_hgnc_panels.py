from django.test import TestCase

from panels_backend.management.commands.panelapp import PanelClass
from panels_backend.models import (
    Panel,
    ClinicalIndication,
    ClinicalIndicationPanel,
    ClinicalIndicationPanelHistory,
)
from panels_backend.management.commands._insert_panel import (
    _disable_custom_hgnc_panels,
)


class TestDisableCustomPanels_NoMatchingHgncPanel(TestCase):
    """
    CASE: In this case, a PanelApp panel is made,
    but there is no same-genes custom panel in the database already.
    EXPECTED: As there is no custom panel in need of deactivating,
    nothing happens.
    """

    def test_no_matching_hgnc_panel(self):
        """
        CASE: No same-genes custom panel in the database already.
        EXPECTED: No db changes made.
        """
        panel = PanelClass(
            id="1000",
            name="A panel name",
            version="1.15",
            panel_source="PanelApp",
            genes=[
                {
                    "gene_data": {
                        "hgnc_id": "HGNC:2000",
                        "gene_name": "your favorite gene 1",
                        "gene_symbol": "YFG1",
                        "alias": None,
                    },
                    "confidence_level": None,
                }
            ],
            regions=[],
        )

        user = None

        _disable_custom_hgnc_panels(panel, user)

        # there's still nothing in the Panels db
        panels_in_db = Panel.objects.all()
        assert len(panels_in_db) == 0


class TestDisableCustomPanels_DeactivateMatchingHgncPanel(TestCase):
    """
    CASE: In this case, a PanelApp panel is made,
    and a custom panel in the database already has the same genes.
    EXPECTED: The custom panel's CI links are deactivated and set to
    pending, and the change is history-logged.
    """

    def setUp(self) -> None:
        self.custom_panel = Panel.objects.create(
            external_id=None,
            panel_name="HGNC:2000",
            panel_source="test directory",
            panel_version=None,
            test_directory=True,
            custom=False,
            pending=False,
        )

        self.ci = ClinicalIndication.objects.create(
            r_code="R1", name="CI", test_method="Example"
        )

        self.cip = ClinicalIndicationPanel.objects.create(
            panel=self.custom_panel,
            clinical_indication=self.ci,
            current=True,
            pending=False,
        )

    def test_deactivate_matching_hgnc_panel(self):
        """
        CASE: In this case, a PanelApp panel is made,
        and a custom panel in the database already has the same genes.
        EXPECTED: The custom panel's CI links are deactivated and set to
        pending, and the change is history-logged.
        """
        panel = PanelClass(
            id="1000",
            name="A panel name",
            version="1.15",
            panel_source="PanelApp",
            genes=[
                {
                    "gene_data": {
                        "hgnc_id": "HGNC:2000",  # note same HGNC ID as in self.custom_panel
                        "gene_name": "your favorite gene 1",
                        "gene_symbol": "YFG1",
                        "alias": None,
                    },
                    "confidence_level": None,
                }
            ],
            regions=[],
        )

        user = None

        _disable_custom_hgnc_panels(panel, user)

        with self.subTest():
            # the original panel's link with its CI, is now inactive and pending
            cips_in_db = ClinicalIndicationPanel.objects.all()
            assert len(cips_in_db) == 1
            assert not cips_in_db[0].current
            assert cips_in_db[0].pending

        with self.subTest():
            # check the above changes were noted in the history table
            history = ClinicalIndicationPanelHistory.objects.all()
            assert len(history) == 1
            assert history[0].clinical_indication_panel == self.cip
            assert (
                history[0].note
                == "Panel of similar genes has been created in PanelApp"
            )
            assert not history[0].user
