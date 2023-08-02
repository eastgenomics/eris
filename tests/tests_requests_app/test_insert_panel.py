from unittest import mock
from django.test import TestCase
from django.db.models import QuerySet

from requests_app.models import \
    Panel, ClinicalIndication, ClinicalIndicationTestMethodHistory, \
        ClinicalIndicationPanel, ClinicalIndicationPanelHistory

from requests_app.management.commands._insert_panel import \
    make_provisional_ci_panel_link


conn = mock.MagicMock()

class test_make_provisional_ci_panel_link_with_panel(TestCase):
    def setUp(self) -> None:
        """
        Start condition: We need a panel, a clinical indication, and a link between them.
        Then we can test whether 'make_provisional_ci_panel_link' correctly 
        makes changes and forms history.
        """
        Panel.objects.create(
            id=1,
            external_id="one_test_panel", \
            panel_name="one_test_panel_name", \
            panel_source="source", \
            panel_version="5"
        )

        ClinicalIndication.objects.create(
            id=1,
            rcode="r_test_cond",
            name="test_condition",
            test_method="WGS",
        )

        ClinicalIndicationPanel.objects.create(
            config_source="unit_test",
            clinical_indication=1,
            panel=1
        )


    def test_with_panel(self):
        """
        Test that when you try to add a new version of a panel, 
        which already has a link to a clinical indication,
        a new CI-Panel link is made, logged, and both the new and old
        link are flagged as needing manual review
        """
        previous_panel_ci_links = ClinicalIndicationPanel.objects.get()
        # Note the panel is the same as in the db, but version is different
        panel_or_ci_instance = Panel.objects.create(
            external_id="one_test_panel", \
            panel_name="one_test_panel_name", \
            panel_source="source", \
            panel_version="6"
        )
        user = "test_user"
        panel_or_ci = "panel"

        # run make_provisional_ci_panel_link on the contents of the isolated database
        make_provisional_ci_panel_link(previous_panel_ci_links, panel_or_ci_instance,
                                            user, panel_or_ci)
        
        # check what's in the database now
        results_ci_link = ClinicalIndicationPanel.objects.all()
        # TODO: mock the QuerySet of expected ClinicalIndicationPanels below
        self.assertEqual(results_ci_link == QuerySet[ClinicalIndicationPanel])

