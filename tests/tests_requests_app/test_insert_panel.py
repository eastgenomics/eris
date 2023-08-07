from unittest import mock, expectedFailure
from django.test import TestCase
from django.db.models import QuerySet
import datetime
from django_mock_queries.query import MockSet, MockModel

from requests_app.models import \
    Panel, ClinicalIndication, ClinicalIndicationTestMethodHistory, \
        ClinicalIndicationPanel, ClinicalIndicationPanelHistory

from requests_app.management.commands._insert_panel import \
    make_provisional_ci_panel_link, _flag_active_links_for_panel


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
            current=True
        )


    def test_flag_active_links_for_panel(self):
        """
        Create a new version of a panel. A panel with the same external ID is
        already linked to a CI in the database.
        Check that the CI-panel link in the database is changed to 'needs review' and has history logged
        """
        new_panel, created = Panel.objects.get_or_create(
            external_id="one_test_panel_id",
            panel_name="one_test_panel_name",
            panel_source="source",
            panel_version="6",
            defaults={
                "panel_source": "test_source",
                "grch37": True,
                "grch38": True,
                "test_directory": False,
            }
        )

        ci_panel_instances = _flag_active_links_for_panel(new_panel.external_id, 
                                                         "test_user")

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


# class test_make_provisional_ci_panel_link_with_panel(TestCase):
   
#     def setUp(self) -> None:
#         """
#         Start condition: We need a panel, a clinical indication, and a link between them.
#         Then we can test whether 'make_provisional_ci_panel_link' correctly 
#         makes changes and forms history.
#         """
#         panel = Panel.objects.create(
#             external_id="one_test_panel_id", \
#             panel_name="one_test_panel_name", \
#             panel_source="source", \
#             panel_version="5"
#         )

#         clin_ind = ClinicalIndication.objects.create(
#             r_code="r_test_cond",
#             name="test_condition",
#             test_method="WGS"
#         )

#         clin_ind_panel = ClinicalIndicationPanel.objects.create(
#             config_source="unit_test",
#             td_version="test_version",
#             clinical_indication=clin_ind,
#             panel=panel,
#             current=True
#         )


#     def test_setup_worked(self):
#         """
#         Just a test to ensure mocking has been set up correctly.
#         There should be a panel object in the mock database.
#         See if this matches what we expect.
#         """
#         fetched_panel = Panel.objects.filter(external_id="one_test_panel_id")
#         fetched_ci = ClinicalIndication.objects.filter(r_code="r_test_cond")
#         fetched_ci_panel = ClinicalIndicationPanel.objects.filter(config_source="unit_test")

#         mock_queryset_panel = MockSet(
#             MockModel(
#             external_id="one_test_panel_id", 
#             panel_name="one_test_panel_name", 
#             panel_source="source", 
#             panel_version="5"
#             )
#         )

#         mock_queryset_ci = MockSet(
#             MockModel(
#             r_code="r_test_cond",
#             name="test_condition",
#             test_method="WGS"
#             )
#         )

#         mock_queryset_ci_panel = MockSet(
#             MockModel(
#                 config_source="unit_test",
#                 td_version="test_version",
#                 current=True,
#                 panel=MockModel(
#                     external_id="one_test_panel_id", 
#                     panel_name="one_test_panel_name", 
#                     panel_source="source", 
#                     panel_version="5"
#                     ),
#                 clinical_indication=MockModel(
#                     r_code="r_test_cond",
#                     name="test_condition",
#                     test_method="WGS"
#                 )
#             )
#         )

#         assert fetched_panel[0].panel_name == mock_queryset_panel[0].panel_name
#         assert fetched_ci[0].name == mock_queryset_ci[0].name
#         assert fetched_ci_panel[0].td_version == mock_queryset_ci_panel[0].td_version
    

#     @expectedFailure
#     def test_setup_worked_inverted(self):
#         fetched_panel = Panel.objects.filter(external_id="one_test_panel_id")
#         fetched_ci = ClinicalIndication.objects.filter(r_code="r_test_cond")
#         fetched_ci_panel = ClinicalIndicationPanel.objects.filter(config_source="unit_test")

#         assert fetched_panel[0].panel_name == "some nonsense" 
#         assert fetched_ci[0].name == "more nonsense"
#         assert fetched_ci_panel[0].td_version == "even more nonsense"


#     def test_with_panel(self):
#         """
#         Test that when you try to add a new version of a panel, 
#         which already has a link to a clinical indication,
#         a new CI-Panel link is made, logged, and both the new and old
#         link are flagged as needing manual review
#         """      
#         previous_panel_ci_links = ClinicalIndicationPanel.objects.filter(current=True)

#         # Note the panel is the same as in the db, but version is different
#         # TODO: it doesn't think the below is a panel - either when I use 'create' or when I mock it

#         new_panel, created = Panel.objects.get_or_create(
#             external_id="one_test_panel_id",
#             panel_name="one_test_panel_name",
#             panel_source="source",
#             panel_version="6",
#             defaults={
#                 "panel_source": "test_source",
#                 "grch37": True,
#                 "grch38": True,
#                 "test_directory": False,
#             }
#         )

#         # fetched_panel = Panel.objects.filter(external_id="one_test_panel_id")
#         # assert len(fetched_panel) == 2

#         # user = "test_user"
#         # panel_or_ci = "panel"


#         # # run make_provisional_ci_panel_link on the contents of the isolated database
#         # test = make_provisional_ci_panel_link(previous_panel_ci_links, new_panel,
#         #                                user, panel_or_ci)
#         # assert test == "1"
#         # TODO: inside the above, I get the error:
#         # ValueError: Cannot assign "4": "ClinicalIndicationPanel.panel" must be a "Panel" instance.


#         # # # get what's in the database now
#         # results_ci_link = ClinicalIndicationPanel.objects.all()

#         # # # TODO: mock the QuerySet of the EXPECTED ClinicalIndicationPanels below

#         # mock_queryset_cip = MockSet(
#         #     MockModel(config_source="test", 
#         #               clinical_indication=MockModel(), 
#         #               panel=MockModel(),
#         #               current=True),
#         #     MockModel(config_source="test", 
#         #               clinical_indication=MockModel(), 
#         #               panel=MockModel(),
#         #               current=True)
#         # )
#         # self.assertEqual(results_ci_link, mock_queryset_cip)

