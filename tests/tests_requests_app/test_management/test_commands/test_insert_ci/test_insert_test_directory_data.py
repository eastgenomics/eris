"""
This script test the function insert_test_directory_data in _insert_ci.py

The few scenarios being tested:
1. missing td_source field in test directory
2. missing td_version in td_source
3. lower td_version than the one in db
4. lower td_version but with --force
5. multiple links with different td_version in db but the function will compare with the latest td_version when seeding td
6. make a new clinical indication and link it to panel
7. change in clinical indication name will flag old and new links
8. change in panels will flag whichever panel is missing in the latest test directory
9. change in test method will flag the clinical indication
10. linking one clinical indication to multiple panel ids, as long as panels are in test directory under the clinical indication, they won't be flagged
11. hgncs type panel making link
12. hgncs type change in panel will flag both old and new links
13. r code that are no longer in test directory will be flagged (backward deactivation)
"""

from django.test import TestCase

from requests_app.models import (
    ClinicalIndicationPanel,
    Panel,
    ClinicalIndication,
    ClinicalIndicationTestMethodHistory,
    TestDirectoryRelease,
    CiPanelTdRelease
)
from requests_app.management.commands._insert_ci import insert_test_directory_data
from requests_app.management.commands.utils import sortable_version
from tests.tests_requests_app.test_management.test_commands.test_insert_panel.test_insert_gene import (
    len_check_wrapper,
    value_check_wrapper,
)


class TestInsertTestDirectoryData(TestCase):
    def setUp(self) -> None:
        """
        We setup the following:
        1. a panel in db
        2. a clinical indication in db
        3. a pre-existing link between the panel and the clinical indication (ClinicalIndicationPanel) 
        with td_version 5.1
        """

        self.panel = Panel.objects.create(
            external_id="123",
            panel_name="test panel",
        )

        self.clinical_indication = ClinicalIndication.objects.create(
            r_code="R123",
            name="test ci",
            test_method="test method",
        )

        self.ci_panel = ClinicalIndicationPanel.objects.create(
            clinical_indication_id=self.clinical_indication.id,
            panel_id=self.panel.id,
            current=True,
            pending=False,
        )
        
        # make a mock link which has td_version 5.1
        self.td_release = TestDirectoryRelease.objects.create(
            release="5.1",
            td_source="td_source",
            config_source="config_source",
            td_date="date")


    def test_missing_td_source(self):
        """
        CASE: a scenario where the test directory's td_source field is missing.
        EXPECT: an assertion error should be raised
        """

        with self.assertRaises(AssertionError):
            insert_test_directory_data(
                {},
                "5.2"
            )  # the third parameter is False. In normal circumstances, it is False by default

    def test_missing_td_version_in_td_source(self):
        """
        scenario where test directory td_source doesn't have a version
        """

        with self.assertRaises(AssertionError):
            insert_test_directory_data({"td_source": ""}, "5.0")

    def test_lower_td_version_will_raise_exception(self):
        """
        CASE: scenario where we are trying to seed with a test directory that is a lower version
        than the one in db
        EXPECT: we expect the function to raise Exception error
        """

        mock_test_directory = {
            "td_source": "rare-and-inherited-disease-national-gnomic-test-directory-v2.0.xlsx",
        }
        version = "2.0"

        with self.assertRaises(Exception):
            insert_test_directory_data(mock_test_directory, version)

    def test_lower_td_version_but_with_force(self):
        """
        --force is a parameter that we can call when seeding test directory
        e.g. command
        python manage.py seed td <td path> --force

        this will force insertion of td into db regardless of td_version
        """
        mock_test_directory = {
            "indications": [],
            "td_source": "rare-and-inherited-disease-national-gnomic-test-directory-v5.0.xlsx",
            "config_source": "config_source"
        }  
        
        version = "5.0"
        # here's a mock version that is lower - v5.0 compared to the v5.1 in setup above

        assert insert_test_directory_data(
            mock_test_directory, version, True
        )  # notice the True for `force` parameter

    def test_that_the_function_will_compare_with_the_latest_td_version(self):
        """
        Imagine that we have multiple ClinicalIndicationPanel links in db, with different td_version:
        e.g.
        link 1 - v4.0
        link 2 - v5.1
        Check that if we seed test directory v4.5 now, the function still raises an Exception
        as the latest td_version in db is v5.1
        """

        ci_pan = ClinicalIndicationPanel.objects.create(
            clinical_indication_id=self.clinical_indication.id,
            panel_id=self.panel.id,
            current=True,
        ) 
        
        rel_4_1 = TestDirectoryRelease.objects.create(release="4.0")
        
        CiPanelTdRelease.objects.create(
            ci_panel=ci_pan,
            td_release=rel_4_1)

        mock_test_directory = {
            "indications": [],
            "td_source": "rare-and-inherited-disease-national-gnomic-test-directory-v5.0.xlsx",
        }

        version = "5.0"

        with self.assertRaises(Exception):
            insert_test_directory_data(mock_test_directory, version)

    def test_make_clinical_indication_and_link_to_panel(self):
        """
        test the core function of given a new clinical indication and its panel
        the function will create a new clinical indication and link it to the panel setup above (self.panel)
        """
        errors = []

        mock_test_directory = {
            "indications": [
                {
                    "name": "Monogenic hearing loss",
                    "code": "R67.1",
                    "test_method": "WES or Large Panel",
                    "panels": ["123"],
                    "original_targets": "Hearing loss (126)",
                    "changes": "No change",
                },
            ],
            "td_source": "rare-and-inherited-disease-national-gnomic-test-directory-v5.2.xlsx",
            "config_source": "230401_RD",
            "date": "230616",
        }

        insert_test_directory_data(mock_test_directory, "5.2", False)

        clinical_indications = ClinicalIndication.objects.all()
        errors += len_check_wrapper(clinical_indications, "clinical indications", 2)

        errors += value_check_wrapper(
            clinical_indications[1].r_code, "clinical indication r code", "R67.1"
        )

        clinical_indication_panels = ClinicalIndicationPanel.objects.all().order_by(
            "id"
        )  # order by id to make sure the first link is the one from setup above
        errors += len_check_wrapper(
            clinical_indication_panels, "clinical indication-panel", 2
        )  # should have 2 links; one from setup and one from the function

        errors += value_check_wrapper(
            clinical_indication_panels[1].clinical_indication.id,
            "clinical indication id",
            clinical_indications[1].id,
        )

        #check there are 2 links to td version
        links = CiPanelTdRelease.objects.all()
        
        errors += len_check_wrapper(links, "ci-panel td-release links matching our ci_panel", 1)

        assert not errors, errors

    def test_that_change_in_clinical_indication_name_will_flag_old_links(self):
        """
        CASE: A clinical indication R123 is renamed from "test ci" to "test ci 2"
        EXPECT: A second clinical indication is made.
        A new link is made between "test ci 2" and the panels that "test ci" is linked to.
        Both these old and new links are flagged for review.
        The new link is linked to a TestDirectoryRelease entry for release 5.2.

        """
        errors = []

        mock_test_directory = {
            "indications": [
                {
                    "name": "test ci 2",  # notice the name change
                    "code": "R123",  # notice the r code is the same
                    "test_method": "WES or Large Panel",
                    "panels": [
                        "123"
                    ],  # notice this is the same panel as the one in setup
                    "original_targets": "Hearing loss (126)",
                    "changes": "No change",
                },
            ],
            "td_source": "rare-and-inherited-disease-national-gnomic-test-directory-v5.2.xlsx",
            "config_source": "230401_RD",
            "date": "230616",
        }

        insert_test_directory_data(mock_test_directory, "5.2")

        clinical_indications = ClinicalIndication.objects.all().order_by("id")
        errors += len_check_wrapper(clinical_indications, "clinical indications", 2)

        errors += value_check_wrapper(
            clinical_indications[1].name, "name", "test ci 2"
        )  # check that new clinical indication is correct

        clinical_indication_panels = ClinicalIndicationPanel.objects.order_by(
            "id"
        ).values(
            "clinical_indication_id__name",
            "clinical_indication_id__r_code",
            "pending",
        )
        errors += len_check_wrapper(
            clinical_indication_panels, "clinical indication-panel", 2
        )  # should have 2 links; one from setup and one from the function

        errors += value_check_wrapper(
            clinical_indication_panels[1]["clinical_indication_id__name"],
            "clinical indication panel name",
            "test ci 2",
        )  # the second link is linked to the new clinical indication

        errors += value_check_wrapper(
            all(
                [
                    ci_panel["clinical_indication_id__r_code"] == "R123"
                    for ci_panel in clinical_indication_panels
                ]
            ),
            "clinical indication id r code",
            True,
        )  # check that both ci-panel links are linked to the same clinical indication (the one in setup)

        # both links are flagged `pending` True
        errors += value_check_wrapper(
            all(
                [
                    ci_panel["pending"] == True
                    for ci_panel in clinical_indication_panels
                ],
            ),
            "clinical indication pending",
            True,
        )  

        #check there is 1 link to the td version (I didn't make a link in setUp for the 'old' CI)
        links = CiPanelTdRelease.objects.all()
        errors += len_check_wrapper(links, "ci-panel td-release links matching our ci_panel", 1)
        errors += value_check_wrapper(links[0].ci_panel.clinical_indication,
                                      "new ci-panel linked to new td-release", 
                                      clinical_indications[1])

        assert not errors, errors

    def test_that_change_in_panels_will_flag_old_links(self):
        """
        scenario where R123 is linked to panel 123 in setup
        in the latest test directory, R123 is linked to panel 234 instead
        panel 123 being missing under R123 will cause it to be flagged for review
        R123 link to panel 234 is fine because it's in the test directory

        we expect the function to create a link between R123 and panel 234 then flag
        the previous link (R123 to panel 123) for review
        """

        errors = []

        # NOTE: normally we run PanelApp API seed before test directory seed
        # thus making sure that Panel 234 is already in the db since PanelApp is where we source our Panel
        # thus here we will need to make panel 234 for this condition to work

        Panel.objects.create(external_id="234", 
                             panel_name="test panel 2")

        mock_test_directory = {
            "indications": [
                {
                    "name": "test ci",
                    "code": "R123",  # same r code
                    "test_method": "WES or Large Panel",
                    "panels": ["234"],  # notice the different panel
                    "original_targets": "Hearing loss (126)",
                    "changes": "No change",
                },
            ],
            "td_source": "rare-and-inherited-disease-national-gnomic-test-directory-v5.2.xlsx",
            "config_source": "230401_RD",
            "date": "230616",
        }

        insert_test_directory_data(mock_test_directory, "5.2")

        clinical_indication_panels = ClinicalIndicationPanel.objects.order_by(
            "id"
        ).values("panel_id__external_id", "clinical_indication_id__r_code", "pending")

        errors += len_check_wrapper(
            clinical_indication_panels, "clinical indication-panel", 2
        )  # should only be 2 links R123 to panel 123 and panel 234

        errors += value_check_wrapper(
            clinical_indication_panels[1]["panel_id__external_id"],
            "clinical indication panel external id",
            "234",
        )  # second link

        errors += value_check_wrapper(
            clinical_indication_panels[1]["clinical_indication_id__r_code"],
            "clinical indication r code",
            "R123",
        )  # second link

        errors += value_check_wrapper(
            clinical_indication_panels[1]["pending"],
            "clinical indication panel 2 pending",
            False,
        )  # this new link should be False

        errors += value_check_wrapper(
            clinical_indication_panels[0]["pending"],
            "clinical indication panel 1 pending",
            True,
        )  # the old link R123 to panel 123 should be flagged

        assert not errors, errors

    def test_that_change_in_test_method_is_recorded(self):
        """
        scenario where a clinical indication changed test method in latest test directory
        """

        mock_test_directory = {
            "indications": [
                {
                    "name": "test ci",  # same name as setup
                    "code": "R123",  # same r code as setup
                    "test_method": "WES or Large Panel",  # notice the different test method
                    "panels": ["123"],  # ignore this
                    "original_targets": "Hearing loss (126)",
                    "changes": "No change",
                },
            ],
            "td_source": "rare-and-inherited-disease-national-gnomic-test-directory-v5.2.xlsx",
            "config_source": "230401_RD",
            "date": "230616",
        }

        insert_test_directory_data(mock_test_directory, "5.2")

        self.clinical_indication.refresh_from_db()

        assert (
            self.clinical_indication.test_method == "WES or Large Panel"
        )  # test method changed
        assert (
            self.clinical_indication.pending == True
        )  # flagged for review due to the change in test method

        assert (
            ClinicalIndicationTestMethodHistory.objects.all().count() == 1
        )  # one test method history record

    def test_linking_one_clinical_indication_to_multiple_panel_ids(self):
        """
        scenario where a clinical indication is linked to multiple panel ids in latest test directory

        we expect the function to create the new clinical indication and link it to both panels
        """
        errors = []

        Panel.objects.create(
            external_id="234",
            panel_name="test panel",
        )  # we make a panel with external id 234

        mock_test_directory = {
            "indications": [
                {
                    "name": "test ci",
                    "code": "R234",  # different r code as setup
                    "test_method": "WES or Large Panel",
                    "panels": ["123", "234"],  # linked to two panels
                    "original_targets": "Hearing loss (126)",
                    "changes": "No change",
                },
            ],
            "td_source": "rare-and-inherited-disease-national-gnomic-test-directory-v5.2.xlsx",
            "config_source": "230401_RD",
            "date": "230616",
        }

        insert_test_directory_data(mock_test_directory, "5.2")

        clinical_indications = ClinicalIndication.objects.all().order_by("id")

        errors += len_check_wrapper(clinical_indications, "clinical indications", 2)
        errors += value_check_wrapper(
            clinical_indications[1].r_code, "r code", "R234"
        )  # the new clinical indication has r code R234

        clinical_indication_panels = ClinicalIndicationPanel.objects.all().order_by(
            "id"
        )

        errors += len_check_wrapper(
            clinical_indication_panels, "clinical indication-panel", 3
        )  # there should be 3 links, one from setup and two from the function (we are looking at the two from the function)

        # errors += value_check_wrapper(
        #     clinical_indication_panels[1].td_version,
        #     "td_version",
        #     sortable_version("5.2"),
        # )
        #TODO: td_version

        # errors += value_check_wrapper(
        #     clinical_indication_panels[1].td_version,
        #     "td_version",
        #     clinical_indication_panels[2].td_version,
        # )

        clinical_indication_panels = ClinicalIndicationPanel.objects.order_by(
            "id"
        ).values("panel_id__external_id", "clinical_indication_id__r_code", "pending")

        assert clinical_indication_panels[1]["panel_id__external_id"] in [
            "123",
            "234",
        ]  # both links are connected to 123 and 234
        assert clinical_indication_panels[2]["panel_id__external_id"] in ["123", "234"]

        errors += value_check_wrapper(
            clinical_indication_panels[1]["clinical_indication_id__r_code"],
            "clinical indication r code",
            "R234",
        )

        errors += value_check_wrapper(
            clinical_indication_panels[2]["clinical_indication_id__r_code"],
            "clinical indication r code",
            clinical_indication_panels[1]["clinical_indication_id__r_code"],
        )  # both links are from R123

        errors += value_check_wrapper(
            clinical_indication_panels[1]["pending"],
            "clinical indication 1 pending",
            False,
        )  # first link is not flagged pending

        errors += value_check_wrapper(
            clinical_indication_panels[2]["pending"],
            "clinical indication 2 pending",
            clinical_indication_panels[1]["pending"],
        )  # same for the second link because they're both in the test directory

        # this is an impossible situation where one R code is connected to two panels
        # NOTE: even in genepanels file generation, this will be flagged up because one clinical indication
        # cannot possibly be linked to two panels, at least I haven't yet seen one
        # but the logic is that both links won't be flagged automatically because they both
        # exist in the test directory

        # NOTE: but this will show up when viewing in the UI as the UI shows a warning when
        # one clinical indication is linked to multiple panels

        assert not errors, errors

    def test_hgncs_type_panel_making_link(self):
        """
        test when a clinical indication have hgncs as panel
        expect function to create or use existing clinical indication (R123 is already in the db from setup)
        expect function to create a new panel (HGNC:1,HGNC:2) and link those two together
        """

        errors = []

        mock_test_directory = {
            "indications": [
                {
                    "name": "test ci",
                    "code": "R123",  # same r code as setup
                    "test_method": "WES or Large Panel",
                    "panels": [
                        "HGNC:1",
                        "HGNC:2",
                    ],  # linked to two hgncs - this will be made into one panel
                    "original_targets": "Hearing loss (126)",
                    "changes": "No change",
                },
            ],
            "td_source": "rare-and-inherited-disease-national-gnomic-test-directory-v5.2.xlsx",
            "config_source": "230401_RD",
            "date": "230616",
        }

        insert_test_directory_data(mock_test_directory, "5.2")

        clinical_indication_panels = ClinicalIndicationPanel.objects.order_by(
            "id"
        ).values("panel_id__panel_name", "clinical_indication_id__r_code")

        errors += value_check_wrapper(
            clinical_indication_panels[1]["panel_id__panel_name"],
            "clinical indication panel name",
            "HGNC:1,HGNC:2",
        )

        errors += value_check_wrapper(
            clinical_indication_panels[1]["clinical_indication_id__r_code"],
            "clinical indication r code",
            "R123",
        )

        assert not errors, errors

    def test_hgncs_type_change_in_panel(self):
        """
        above test for linking a clinical indication to hgnc-type panels
        what if the same clinical indication (R123) changes its hgncs in the next test directory

        example:
            R123 is linked to panel (HGNC:1,HGNC:2) - already in db
            in next test directory, R123 have panels: [HGNC:1, HGNC:3]

        we expect the function to make a new panel HGNC1,HGNC3 and link it to R123
        then flag both links for review
        """

        errors = []

        mock_panel = Panel.objects.create(
            panel_name="HGNC:1,HGNC:2",
            test_directory=True,  # notice this is True. All panels that come from test directory especially hgncs have this value as True
        )

        mock_clinical_indication = ClinicalIndication.objects.create(
            r_code="R234",
            name="test ci 2",
        )

        ClinicalIndicationPanel.objects.create(
            panel_id=mock_panel.id,
            clinical_indication_id=mock_clinical_indication.id,
            current=True,
        )  # make a mock link between R123 and HGNC:1,HGNC:2

        mock_test_directory = {
            "indications": [
                {
                    "name": "test ci",
                    "code": "R123",
                    "test_method": "WES or Large Panel",
                    "panels": ["123"],
                    "original_targets": "Hearing loss (126)",
                    "changes": "No change",
                },
                {
                    "name": "test ci 2",
                    "code": "R234",  # notice r code
                    "test_method": "WES or Large Panel",
                    "panels": [
                        "HGNC:1",
                        "HGNC:3",
                    ],  # this is different from HGNC:1 and HGNC:2
                    "original_targets": "Hearing loss (126)",
                    "changes": "No change",
                },
            ],
            "td_source": "rare-and-inherited-disease-national-gnomic-test-directory-v5.2.xlsx",
            "config_source": "230401_RD",
            "date": "230616",
        }

        insert_test_directory_data(mock_test_directory, "5.2")

        clinical_indication_panels = ClinicalIndicationPanel.objects.order_by(
            "id"
        ).values("panel_id__panel_name", "clinical_indication_id__r_code", "pending")

        # NOTE: the first clinical indication-panel link is made in setup above
        # the second link is made between R234 and HGNC:1,HGNC:2
        # we expect the third link to be made by the function between R234 and HGNC:1,HGNC:3

        errors += len_check_wrapper(
            clinical_indication_panels, "clinical indication-panel", 3
        )

        errors += value_check_wrapper(
            clinical_indication_panels[0]["pending"],
            "first clinical indication-panel pending",
            False,
        )  # first link shouldn't be touched

        errors += value_check_wrapper(
            clinical_indication_panels[1]["pending"],
            "second clinical indication-panel pending",
            True,
        )  # second link is flagged pending

        errors += value_check_wrapper(
            clinical_indication_panels[2]["pending"],
            "third clinical indication-panel pending",
            True,
        )  # third link is flagged pending

        errors += value_check_wrapper(
            clinical_indication_panels[2]["panel_id__panel_name"],
            "third clinical indication-panel panel name",
            "HGNC:1,HGNC:3",
        )  # R234 linked to HGNC:1,HGNC:3

        errors += value_check_wrapper(
            clinical_indication_panels[2]["clinical_indication_id__r_code"],
            "third clinical indication-panel r code",
            "R234",
        )  # R234 linked to HGNC:1,HGNC:3

        assert not errors, errors

    def test_that_r_code_that_are_no_longer_in_test_directory_will_be_flagged(self):
        """
        scenario where R123 is no longer in the latest test directory thus we expect
        the function to flag the R123 linked to panel 123 link for review (the link we made in setup)
        """

        mock_test_directory = {
            "indications": [],  # notice this empty list of indications
            "td_source": "rare-and-inherited-disease-national-gnomic-test-directory-v5.2.xlsx",
            "config_source": "230401_RD",
            "date": "230616",
        }

        insert_test_directory_data(mock_test_directory, "5.2")

        clinical_indication_panels = ClinicalIndicationPanel.objects.all()

        assert len(clinical_indication_panels) == 1
        assert clinical_indication_panels[0].pending == True  # flagged for review
