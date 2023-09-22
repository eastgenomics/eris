from unittest import mock, expectedFailure
from django.test import TestCase
from django.db.models import QuerySet
import datetime
from django_mock_queries.query import MockSet, MockModel

from requests_app.models import (
    Panel,
    ClinicalIndication,
    ClinicalIndicationPanel,
    ClinicalIndicationPanelHistory,
)

from requests_app.management.commands._insert_ci import (
    flag_clinical_indication_panel_for_review,
    provisionally_link_clinical_indication_to_panel,
)

from requests_app.management.commands.history import History


class TestFlagCurrentLinksForClinicalIndication(TestCase):
    def setUp(self) -> None:
        """
        Start condition: We need a panel, at least one clinical indication, and a CURRENT link between them.
        Then we can test whether the function correctly sets the link to False and logs it.
        """
        self.first_panel = Panel.objects.create(
            external_id="one_test_panel_id",
            panel_name="one_test_panel_name",
            panel_source="source",
            panel_version="5",
        )

        self.first_clin_ind = ClinicalIndication.objects.create(
            r_code="r_test_cond", name="test_condition", test_method="WGS"
        )

        self.first_clin_ind_panel = ClinicalIndicationPanel.objects.create(
            config_source="unit_test",
            td_version="test_version",
            clinical_indication=self.first_clin_ind,
            panel=self.first_panel,
            current=True,
            pending=False,
        )

    def test_flag_current_links_for_ci_panel(self):
        """
        For a clinical indication-panel object: change 'pending' to True and log this in history
        Function may be used when a new panel or CI is added, and the links to the old version need
        to be nullified for manual review.
        """

        # find our CI-panel entry in the test database. It should be current and NOT pending
        previous_ci_panel = ClinicalIndicationPanel.objects.get(
            id=self.first_clin_ind_panel.pk
        )
        assert previous_ci_panel.pending == False

        # Run the function under test - this should find and change the CI-panel entry in the database
        flag_clinical_indication_panel_for_review(previous_ci_panel, "test_user")

        # now get our entry from the database again - it should have been changed
        post_change_ci_panel = ClinicalIndicationPanel.objects.get(
            id=self.first_clin_ind_panel.pk
        )
        assert post_change_ci_panel.pending == True

        # check that a history entry exists for the change
        history = ClinicalIndicationPanelHistory.objects.get(id=post_change_ci_panel.pk)
        assert history.user == "test_user"
        assert (
            history.note
            == "Flagged for manual review - new clinical indication provided"
        )


class TestMakeProvisionalCiPanelLinkWithCi(TestCase):
    def setUp(self) -> None:
        """
        Start condition: We need a panel, a clinical indication, and a link between them.
        Then we can test whether the function correctly
        makes changes and forms history.
        """
        self.panel = Panel.objects.create(
            external_id="one_test_panel_id",
            panel_name="one_test_panel_name",
            panel_source="source",
            panel_version="5",
        )

        self.clin_ind = ClinicalIndication.objects.create(
            r_code="r_test_cond", name="test_condition", test_method="WGS"
        )

    def test_existing_panel_makes_new_link(self):
        """
        Test function which makes a new CI-Panel link and logs it. The link should be flagged as
        'pending' to pull it up for manual review.
        """

        ci_panel = provisionally_link_clinical_indication_to_panel(
            self.panel.pk, self.clin_ind.pk, "I'm a unit test"
        )

        # Get the link from the database to check how it shows up there, rather than using the returned
        # value
        # it should be 'current' and 'pending'

        new_ci_link = ClinicalIndicationPanel.objects.filter(id=ci_panel.pk)
        assert len(new_ci_link) == 1
        assert type(new_ci_link) == QuerySet

        first_entry = new_ci_link[0]
        assert first_entry.pending == True
        assert first_entry.current == True

        # Check we have only 1 entry in this table
        links = ClinicalIndicationPanel.objects.all()
        assert len(links) == 1

        # Check for a single history record for ClinicalIndicationPanel, with correct ID and message
        history = ClinicalIndicationPanelHistory.objects.all()
        assert len(history) == 1
        history_first = history.all()[:1].get()
        assert history_first.user == "I'm a unit test"
        assert history_first.note == History.auto_created_clinical_indication_panel()
        assert history_first.clinical_indication_panel == first_entry
