from django.test import TestCase

from requests_app.models import (
    ClinicalIndication,
    Panel,
    ClinicalIndicationPanel,
    ClinicalIndicationPanelHistory,
)
from requests_app.management.commands._insert_ci import _flag_panels_removed_from_test_directory
from requests_app.management.commands.history import History

class TestPanelsFlaggedWhenNoLongerInTd(TestCase):
    """
    CASE: We have list of td-file panels, some are current, some are not.
    EXPECT: Current panels which are NOT in the td-files list should be set to current=False, pending=True,
    and history-logged
    Current panels which ARE in the td-files should be skipped, remaining current with no history data

    N.B. that the case where a CiPanel IS in the td-files list, and is NOT CURRENT, shouldn't
    be possible - because we only run _flag_panels_removed_from_test_directory after we've already made entries for everything in the
    td-files list
    """
    def setUp(self) -> None:
        # make two CURRENT Panels
        self.ci = ClinicalIndication.objects.create(
            r_code="R454",
            name="Current Absent CI",
            test_method="wgs"
        )
        self.panel_current_absent = Panel.objects.create(
            external_id="3",
            panel_name="Current Absent Panel",
            panel_source="PanelApp",
            panel_version="500"
            )
        self.cip_current_absent = ClinicalIndicationPanel.objects.create(
            clinical_indication=self.ci,
            panel=self.panel_current_absent,
            current=True
        )

        self.panel_current_present = Panel.objects.create(
            external_id="4",
            panel_name="Current Present Panel",
            panel_source="PanelApp",
            panel_version="50",
        )
        self.cisp_current_present = ClinicalIndicationPanel.objects.create(
            clinical_indication=self.ci,
            panel=self.panel_current_present,
            current=True,
            pending=False
        )

        # make a list of panels which ARE PRESENT in the current td - from which one of the current
        # CiPanels will be missing
        self.current_td_panels = ["4"]
    
    def test_flag_panels_removed_from_test_directory(self):
        """
        CASE: We have list of td-file panels, some are current, some are not. Some are in the Panel table, 
        some are not.
        EXPECT: Current panels which are NOT in the td-files list should be set to current=False, 
        pending=True, and history-logged
        Current panels which ARE in the td-files should be skipped, remaining current with no history data
        """
        _flag_panels_removed_from_test_directory(self.ci, self.current_td_panels, "test user")
        
        # check that the panel with the external ID '3', which is absent from the
        # current td, is set to current=False and pending=True
        panel_ext_3 = ClinicalIndicationPanel.objects.filter(panel__external_id="3")
        with self.subTest():
            assert len(panel_ext_3) == 1
            assert not panel_ext_3[0].current
            assert panel_ext_3[0].pending

        # check history note
        hist = ClinicalIndicationPanelHistory.objects.all()
        with self.subTest():
            assert len(hist) == 1
            assert hist[0].note == History.flag_clinical_indication_panel(
                        "ClinicalIndicationPanel does not exist in TD"
                    )
            
        # check that the panel with the external ID '4', which is PRESENT IN the
        # current td, is still set to current=True
        panel_ext_4 = ClinicalIndicationPanel.objects.filter(panel__external_id="4")
        with self.subTest():
            assert len(panel_ext_4) == 1
            assert panel_ext_4[0].current
            assert not panel_ext_4[0].pending
