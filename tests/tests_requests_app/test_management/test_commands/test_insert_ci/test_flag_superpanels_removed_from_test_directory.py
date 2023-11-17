from django.test import TestCase

from requests_app.management.commands.utils import sortable_version
from requests_app.models import (
    ClinicalIndication,
    Panel,
    SuperPanel,
    ClinicalIndicationSuperPanel,
    ClinicalIndicationPanelHistory,
    TestDirectoryRelease,
    CiPanelTdRelease,
)
from requests_app.management.commands._insert_ci import _flag_panels_removed_from_test_directory
from tests.tests_requests_app.test_management.test_commands.test_insert_panel.test_insert_gene import (
    len_check_wrapper,
    value_check_wrapper,
)


class TestSuperpanelsFlaggedWhenNoLongerInTd(TestCase):
    """
    CASE: We have list of td-file panels, some are current, some are not. Some are in the SuperPanel table, 
    some are not.
    EXPECT: Current Superpanels which are NOT in the td-files list should be set to current=False, pending=True,
    and history-logged
    Current Superpanels which ARE in the td-files should be skipped, remaining current with no history data

    N.B. that the case where a CiSuperpanel IS in the td-files list, and is NOT CURRENT, shouldn't
    be possible - because we only run _flag_panels_removed_from_test_directory after we've already made entries for everything in the
    td-files list
    """
    def setUp(self) -> None:
        # make two CURRENT CiSuperPanels
        self.ci_current_absent = ClinicalIndication.objects.create(

        )
        self.superpanel_current_absent = SuperPanel.objects.create(
            current=True
        )
        self.cisp_current_absent = ClinicalIndicationSuperPanel.objects.create(
            clinical_indication=self.ci_current_absent,
            superpanel=self.superpanel_current_absent
        )

        self.ci_current_present = ClinicalIndication.objects.create(

        )
        self.superpanel_current_present = SuperPanel.objects.create(
            current=True
        )
        self.cisp_current_present = ClinicalIndicationSuperPanel.objects.create(
            clinical_indication=self.ci_current_present,
            superpanel=self.superpanel_current_present
        )


        # make a NOT CURRENT CiSuperPanel
        self.cisp_not_current = 

        # make a list of panels which ARE PRESENT in the current td - from which one of the current
        # CiSuperPanels will be missing
    
    def test_flag_panels_removed_from_test_directory(self):
        """
        CASE: We have list of td-file panels, some are current, some are not. Some are in the SuperPanel table, 
        some are not.
        EXPECT: Current Superpanels which are NOT in the td-files list should be set to current=False, pending=True,
        and history-logged
        Current Superpanels which ARE in the td-files should be skipped, remaining current with no history data
        """
        return None
    