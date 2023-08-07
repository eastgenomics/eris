from unittest import mock, expectedFailure
from django.test import TestCase
from django.db.models import QuerySet
import datetime
from django_mock_queries.query import MockSet, MockModel

from requests_app.models import \
    Panel, ClinicalIndication, ClinicalIndicationTestMethodHistory, \
        ClinicalIndicationPanel, ClinicalIndicationPanelHistory

from requests_app.management.commands._insert_ci import \
    _provisionally_link_new_ci_version_to_panel, _flag_active_links_for_ci

class TestFlagActiveLinksForClinicalIndication(TestCase):

    def setUp(self) -> None:
        """
        Start condition: We need a panel, at least one clinical indication, and a CURRENT link between them.
        Then we can test whether they correctly have flags applied.
        """
        self.first_panel = Panel.objects.create(
            external_id="one_test_panel_id", \
            panel_name="one_test_panel_name", \
            panel_source="source", \
            panel_version="5"
        )

        self.first_clin_ind = ClinicalIndication.objects.create(
            r_code="r_test_cond",
            name="test_condition",
            test_method="WGS"
        )

        self.first_clin_ind_panel = ClinicalIndicationPanel.objects.create(
            config_source="unit_test",
            td_version="test_version",
            clinical_indication=self.first_clin_ind,
            panel=self.first_panel,
            current=True
        )


    def test_flag_active_links_for_ci(self):
        """
        Create a new version of a clinical indication. A CI with the same r code is
        already linked to a panel in the database.
        Check that the CI-panel link in the database is changed to 'needs review' and has history logged
        """

        # Make a clinical indication which has the same R code as the existing one 
        # Check they are both in the test database
        new_ci, created = ClinicalIndication.objects.get_or_create(
            r_code="r_test_cond",
            name="renamed_condition",
            test_method="panel"
        )
        assert len(ClinicalIndication.objects.filter(r_code="r_test_cond")) == 2

        # Run the function under test
        ci_panel_instances = _flag_active_links_for_ci(new_ci.r_code, "test_user")

        # We expect a QuerySet of 1 ClinicalIndicationPanel result, because this function only flags 
        # existing CI-Panel links, and the new CI hasn't had one made yet
        assert len(ci_panel_instances) == 1
        assert type(ci_panel_instances) == QuerySet

        # Check that the ClinicalIndicationPanel has been set to needs_review = True
        ci_panel_first = ci_panel_instances.all()[:1].get()
        assert ci_panel_first.config_source == "unit_test"
        assert ci_panel_first.needs_review == True

        # Check for a single history record for ClinicalIndicationPanel, with correct ID and message
        history = ClinicalIndicationPanelHistory.objects.all()
        assert len(history) == 1
        history_first = history.all()[:1].get()
        assert history_first.user == "test_user"
        assert history_first.note == "Flagged for manual review - new clinical indication provided"
        assert history_first.clinical_indication_panel == ci_panel_first

