from unittest import mock, expectedFailure
from django.test import TestCase
from django.db.models import QuerySet
import datetime
from django_mock_queries.query import MockSet, MockModel

from requests_app.models import \
    Panel, ClinicalIndication, ClinicalIndicationTestMethodHistory, \
        ClinicalIndicationPanel, ClinicalIndicationPanelHistory

from requests_app.management.commands._insert_panel import \
    _provisionally_link_new_panel_version_to_ci, _flag_current_links_for_panel
from requests_app.management.commands._utils import sortable_version


conn = mock.MagicMock()

class TestFlagActiveLinksForPanel(TestCase):

    def setUp(self) -> None:
        """
        Start condition: We need a panel, at least one clinical indication, and a CURRENT link between them.
        Then we can test whether they correctly have flags applied.
        """
        panel = Panel.objects.create(
            external_id="one_test_panel_id", \
            panel_name="one_test_panel_name", \
            panel_source="source", \
            panel_version="5"
        )

        clin_ind = ClinicalIndication.objects.create(
            r_code="r_test_cond",
            name="test_condition",
            test_method="WGS"
        )

        clin_ind_panel = ClinicalIndicationPanel.objects.create(
            config_source="unit_test",
            td_version="test_version",
            clinical_indication=clin_ind,
            panel=panel,
            current=True,
        )


    def test_flag_current_links_for_panel(self):
        """
        Create a new version of a panel. A panel with the same external ID is
        already linked to a CI in the database.
        Check that the CI-panel link in the database is changed to 'needs review' and has history logged
        """
        new_panel, created = Panel.objects.get_or_create(
            external_id="one_test_panel_id",
            panel_name="one_test_panel_name",
            panel_source="source",
            panel_version="6"
        )

        # Set up a search of previous panel instances
        previous_panel_instances: list[Panel] = Panel.objects.filter(
            external_id="one_test_panel_id").exclude(pk=new_panel.id)

        assert len(previous_panel_instances) == 1
        prev_panel = previous_panel_instances[0]

        ci_panel_instances = _flag_current_links_for_panel(prev_panel, "test_user")

        # Expect a QuerySet of 1 ClinicalIndicationPanel result, because this function only flags 
        # existing CI-Panel links, and the new panel hasn't had one made yet
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
        assert history_first.note == "Flagged for manual review - new panel version pulled from PanelApp API"
        assert history_first.clinical_indication_panel == ci_panel_first


class TestMakeProvisionalCiPanelLinkWithPanel(TestCase):
   
    def setUp(self) -> None:
        """
        Start condition: We need a panel, a clinical indication, and a link between them.
        Then we can test whether the function correctly 
        makes changes and forms history.
        """
        panel = Panel.objects.create(
            external_id="one_test_panel_id", \
            panel_name="one_test_panel_name", \
            panel_source="source", \
            panel_version="5"
        )

        clin_ind = ClinicalIndication.objects.create(
            r_code="r_test_cond",
            name="test_condition",
            test_method="WGS"
        )

        clin_ind_panel = ClinicalIndicationPanel.objects.create(
            config_source="unit_test",
            td_version="test_version",
            clinical_indication=clin_ind,
            panel=panel,
            current=True,
            needs_review=False
        )


    def test_makes_new_link(self):
        """
        Test that when you try to add a new version of a panel, 
        which already has a link to a clinical indication,
        a new CI-Panel link is made, logged, and both the new and old
        link are flagged as needing manual review
        """      
        previous_panel_ci_links = ClinicalIndicationPanel.objects.filter(current=True)

        new_panel =  Panel.objects.create(
            external_id="one_test_panel_id", \
            panel_name="one_test_panel_name", \
            panel_source="source", \
            panel_version="6"
        )

        _provisionally_link_new_panel_version_to_ci(previous_panel_ci_links, new_panel, 
                                                    "I'm a unit test")
        
        # There should now be an CURRENT CI-panel link for this panel, using the previous data
        # It will have a version of 6, it will be 'current' and it will need review
        new_panel_link = ClinicalIndicationPanel.objects.filter(panel__panel_version=6)
        assert len(new_panel_link) == 1
        assert type(new_panel_link) == QuerySet
        first_entry = new_panel_link[0]
        assert first_entry.needs_review == True

        # Check we have 2 current links in total - as the old one is still present
        links = ClinicalIndicationPanel.objects.filter(current=True)
        assert len(links) == 2

        # Check that history is created
        hist = ClinicalIndicationPanelHistory.objects.filter(clinical_indication_panel=new_panel_link[0])
        assert len(hist) == 1
        first_hist = hist[0]
        assert first_hist.note == "Auto-created CI-panel link based on information available for an " +\
            "earlier panel version - needs manual review"
        assert first_hist.user == "I'm a unit test"
        