from django.test import TestCase

from panels_backend.models import (
    ClinicalIndication,
    SuperPanel,
    ClinicalIndicationSuperPanel,
    ClinicalIndicationSuperPanelHistory,
)
from panels_backend.management.commands._insert_ci import (
    _flag_superpanels_removed_from_test_directory,
)
from panels_backend.management.commands.history import History


class TestSuperpanelsFlaggedWhenNoLongerInTd(TestCase):
    """
    CASE: We have list of td-file panels, some are current, some are not. Some are in the SuperPanel table,
    some are not.
    EXPECT: Current Superpanels which are NOT in the td-files list should be set to current=False, pending=True,
    and history-logged
    Current Superpanels which ARE in the td-files should be skipped, remaining current with no history data

    N.B. that the case where a CiSuperpanel IS in the td-files list, and is NOT CURRENT, shouldn't
    be possible - because we only run _flag_superpanels_removed_from_test_directory after we've already made entries for everything in the
    td-files list
    """

    def setUp(self) -> None:
        # make two CURRENT CiSuperPanels
        self.ci = ClinicalIndication.objects.create(
            r_code="R454", name="Current Absent CI", test_method="wgs"
        )
        self.superpanel_current_absent = SuperPanel.objects.create(
            external_id="3",
            panel_name="Current Absent Panel",
            panel_source="PanelApp",
            panel_version="500",
        )
        self.cisp_current_absent = ClinicalIndicationSuperPanel.objects.create(
            clinical_indication=self.ci,
            superpanel=self.superpanel_current_absent,
            current=True,
        )

        self.superpanel_current_present = SuperPanel.objects.create(
            external_id="4",
            panel_name="Current Present Panel",
            panel_source="PanelApp",
            panel_version="50",
        )
        self.cisp_current_present = (
            ClinicalIndicationSuperPanel.objects.create(
                clinical_indication=self.ci,
                superpanel=self.superpanel_current_present,
                current=True,
                pending=False,
            )
        )

        # make a list of panels which ARE PRESENT in the current td - from which one of the current
        # CiSuperPanels will be missing
        self.current_td_panels = ["4"]

    def test_flag_superpanels_removed_from_test_directory(self):
        """
        CASE: We have list of td-file superpanels, some are current, some are not. Some are in the SuperPanel table,
        some are not.
        EXPECT: Current Superpanels which are NOT in the td-files list should be set to current=False,
        pending=True, and history-logged
        Current Superpanels which ARE in the td-files should be skipped, remaining current with no history data
        """
        _flag_superpanels_removed_from_test_directory(
            self.ci, self.current_td_panels, "test user"
        )

        # check that the superpanel with the external ID '3', which is absent from the
        # current td, is set to current=False and pending=True
        superpanel_ext_3 = ClinicalIndicationSuperPanel.objects.filter(
            superpanel__external_id="3"
        )
        with self.subTest():
            assert len(superpanel_ext_3) == 1
            assert not superpanel_ext_3[0].current
            assert superpanel_ext_3[0].pending

        # check history note
        hist = ClinicalIndicationSuperPanelHistory.objects.all()
        with self.subTest():
            assert len(hist) == 1
            assert hist[0].note == History.flag_clinical_indication_panel(
                "Superpanel ID no longer attached to clinical indication in TD"
            )

        # check that the superpanel with the external ID '4', which is PRESENT IN the
        # current td, is still set to current=True
        superpanel_ext_4 = ClinicalIndicationSuperPanel.objects.filter(
            superpanel__external_id="4"
        )
        with self.subTest():
            assert len(superpanel_ext_4) == 1
            assert superpanel_ext_4[0].current
            assert not superpanel_ext_4[0].pending
