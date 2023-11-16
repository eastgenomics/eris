"""
This file contains tests for the smaller functions in the insert_ci command.
- _backward_deactivate
- flag_clinical_indication_panel_for_review
- provisionally_link_clinical_indication_to_panel
- _retrieve_panel_from_pa_id
- _retrieve_unknown_metadata_records
- _make_provisional_test_method_change
"""

from django.test import TestCase
from requests_app.models import (
    ClinicalIndication,
    Panel,
    SuperPanel,
    ClinicalIndicationPanel,
    ClinicalIndicationSuperPanel,
    ClinicalIndicationPanelHistory,
    ClinicalIndicationSuperPanelHistory,
    ClinicalIndicationTestMethodHistory,
    TestDirectoryRelease,
)
from requests_app.management.commands.utils import sortable_version
from requests_app.management.commands._insert_ci import (
    _backward_deactivate,
    flag_clinical_indication_panel_for_review,
    flag_clinical_indication_superpanel_for_review,
    provisionally_link_clinical_indication_to_panel,
    provisionally_link_clinical_indication_to_superpanel,
    _retrieve_panel_from_pa_id,
    _retrieve_unknown_metadata_records,
    _make_provisional_test_method_change,
)


class TestBackwardDeactivation(TestCase):
    def setUp(self) -> None:
        self.first_clinical_indication = ClinicalIndication.objects.create(
            r_code="R123", name="Test CI", test_method="Test method"
        )

        self.first_panel = Panel.objects.create(
            external_id=123,
            panel_name="Test panel",
            panel_version=sortable_version("1.15"),
        )

        self.first_clinical_indication_panel = ClinicalIndicationPanel.objects.create(
            clinical_indication_id=self.first_clinical_indication.id,
            panel_id=self.first_panel.id,
            current=True,
        )

    def test_that_link_will_be_flagged_if_not_exist(self):
        """
        If a clinical indication (R code) doesn't exist in the seeded test directory
        it should be flagged by this function

        example:
            - R123 exists in the db
            - but R123 no longer exist in the latest test directory
            - thus any panels linked to R123 (clinical indication-panel) should be flagged for review
        """

        mock_test_directory = (
            []
        )  # notice this empty test directory which simulate a test directory with no R123

        _backward_deactivate(mock_test_directory, "test")

        self.first_clinical_indication_panel.refresh_from_db()

        assert self.first_clinical_indication_panel.pending == True
        assert (
            ClinicalIndicationPanelHistory.objects.count() == 1
        )  # there should be one history recorded
        assert (
            self.first_clinical_indication_panel.current == False
        )  # active status should be False

    def test_that_link_will_not_be_flagged_if_exist(self):
        """
        If a clinical indication (R code) exist in the seeded test directory
        nothing should happen to it - "not flagged for review"

        example:
            - R123 exists in the db
            - R123 exist in the latest test directory
            - thus nothing should happen, the link shouldn't be flagged
        """
        mock_test_directory = [{"code": "R123"}]

        _backward_deactivate(mock_test_directory, "test")

        self.first_clinical_indication_panel.refresh_from_db()

        assert self.first_clinical_indication_panel.pending == False
        assert (
            self.first_clinical_indication_panel.current == True
        )  # link should still be active


class TestFlagClinicalIndicationPanelForReview(TestCase):
    """
    Tests that flagging Clinical Indication - Panel links works correctly
    """

    def setUp(self) -> None:
        self.first_clinical_indication = ClinicalIndication.objects.create(
            r_code="R123", name="Test CI", test_method="Test method"
        )

        self.first_panel = Panel.objects.create(
            external_id=123,
            panel_name="Test panel",
            panel_version=sortable_version("1.15"),
        )

        self.first_clinical_indication_panel = ClinicalIndicationPanel.objects.create(
            clinical_indication_id=self.first_clinical_indication.id,
            panel_id=self.first_panel.id,
            current=True,
        )

    def test_that_link_will_be_flagged_and_history_recorded(self):
        """
        test that given a clinical indication-panel link, the link will be flagged for review and current set to False
        and history recorded in ClinicalIndicationPanelHistory
        """

        flag_clinical_indication_panel_for_review(
            self.first_clinical_indication_panel, "test"
        )

        self.first_clinical_indication_panel.refresh_from_db()

        assert self.first_clinical_indication_panel.pending == True
        assert self.first_clinical_indication_panel.current == False

        assert (
            ClinicalIndicationPanelHistory.objects.count() == 1
        )  # one history recorded


class TestFlagClinicalIndicationSuperpanelForReview(TestCase):
    """
    Tests that flagging Clinical Indication - SuperPanel links works correctly
    """

    def setUp(self) -> None:
        self.first_clinical_indication = ClinicalIndication.objects.create(
            r_code="R123", name="Test CI", test_method="Test method"
        )

        self.first_superpanel = SuperPanel.objects.create(
            external_id=123,
            panel_name="Test panel",
            panel_version=sortable_version("1.15"),
        )

        self.first_clinical_indication_superpanel = (
            ClinicalIndicationSuperPanel.objects.create(
                clinical_indication=self.first_clinical_indication,
                superpanel=self.first_superpanel,
                current=True,
            )
        )

    def test_that_link_will_be_flagged_and_history_recorded(self):
        """
        test that given a clinical indication-superpanel link, the link will be
        flagged for review and current set to False
        and history recorded in ClinicalIndicationSuperPanelHistory
        """

        flag_clinical_indication_superpanel_for_review(
            self.first_clinical_indication_superpanel, "test"
        )

        self.first_clinical_indication_superpanel.refresh_from_db()

        assert self.first_clinical_indication_superpanel.pending
        assert not self.first_clinical_indication_superpanel.current

        assert (
            ClinicalIndicationSuperPanelHistory.objects.count() == 1
        )  # one history recorded


class TestProvisionallyLinkClinicalIndicationToPanel(TestCase):
    """
    Tests for the function which automatically links a new version/name of a panel,
    to the same clinical indication that is linked to an earlier version of the panel.
    """

    def setUp(self) -> None:
        self.first_clinical_indication = ClinicalIndication.objects.create(
            r_code="R123", name="Test CI", test_method="Test method"
        )

        self.second_clinical_indication = ClinicalIndication.objects.create(
            r_code="R123", name="Test CI 2", test_method="Test method"
        )

        self.first_panel = Panel.objects.create(
            external_id=123,
            panel_name="Test panel",
            panel_version=sortable_version("1.15"),
        )

        self.first_clinical_indication_panel = ClinicalIndicationPanel.objects.create(
            clinical_indication_id=self.first_clinical_indication.id,
            panel_id=self.first_panel.id,
            current=True,
            pending=False,
        )

        self.td_version = TestDirectoryRelease.objects.create(release="2.1.0")

    def test_that_existing_link_is_flagged(self):
        """
        `provisionally_link_clinical_indication_to_panel` basically
        link a panel-id to a clinical indication-id to create a clinical indication-panel link

        - the general output is that the link will be created but also flagged for review (expect `pending` to be True)
        - there should be a link made between Ci-Panel and the test directory release
        - we expect this behaviour for both new or existing clinica indication-panel link

        below we test for an existing link
        example:
            panel 123 is already linked to clinical indication R123 as we setup above (with `pending` set to False)
            we expect the `pending` to turn True after calling `provisionally_link_clinical_indication_to_panel` on it
        """

        provisionally_link_clinical_indication_to_panel(
            self.first_panel.id,
            self.first_clinical_indication.id,
            "test",
            self.td_version,
        )  # this is an existing link in db

        self.first_clinical_indication_panel.refresh_from_db()

        # check that the ci-panel is set to pending
        with self.subTest():
            assert self.first_clinical_indication_panel.pending == True

        # test that a release was linked to the ci-panel
        with self.subTest():
            releases = TestDirectoryRelease.objects.all()
            assert len(releases) == 1
            assert releases[0].release == "2.1.0"

    def test_that_new_link_is_flagged(self):
        """
        we test for a new link (not existing in db) - self.second_clinical_indication is not linked to self.first_panel in setup
        `provisionally_link_clinical_indication_to_panel` should create the link and flag it for review
        """
        provisionally_link_clinical_indication_to_panel(
            self.first_panel.id,
            self.second_clinical_indication.id,
            "test",
            self.td_version,
        )

        # test a new ci-panel link is made and flagged for review
        with self.subTest():
            assert ClinicalIndicationPanel.objects.count() == 2  # one new link created
            new_link = ClinicalIndicationPanel.objects.last()

            assert new_link.pending == True  # new link should be flagged for review

        # test that a release was linked to the ci-panel
        with self.subTest():
            releases = TestDirectoryRelease.objects.all()
            assert len(releases) == 1
            assert releases[0].release == "2.1.0"


class TestProvisionallyLinkClinicalIndicationToSuperPanel(TestCase):
    """
    Tests for the function which automatically links a new version/name of a superpanel,
    to the same clinical indication that is linked to an earlier version of the superpanel.
    """

    def setUp(self) -> None:
        self.first_clinical_indication = ClinicalIndication.objects.create(
            r_code="R123", name="Test CI", test_method="Test method"
        )

        self.second_clinical_indication = ClinicalIndication.objects.create(
            r_code="R123", name="Test CI 2", test_method="Test method"
        )

        self.first_superpanel = SuperPanel.objects.create(
            external_id=123,
            panel_name="Test panel",
            panel_version=sortable_version("1.15"),
        )

        self.td_version = TestDirectoryRelease.objects.create(release="5.0")

        self.first_clinical_indication_superpanel = (
            ClinicalIndicationSuperPanel.objects.create(
                clinical_indication=self.first_clinical_indication,
                superpanel=self.first_superpanel,
                current=True,
                pending=False,
            )
        )

    def test_that_existing_superpanel_link_is_flagged(self):
        """
        `provisionally_link_clinical_indication_to_superpanel` links a panel
        to a clinical indication to create a clinical indication-superpanel
        link

        - the general output is that the link will be created but also flagged for
        review (expect `pending` to be True)
        - we expect this behaviour for both new or existing clinical
        indication-superpanel link

        below we test for an existing link
        example:
            superpanel 123 is already linked to clinical indication R123 as we setup
            above (with `pending` set to False)
            we expect the `pending` to turn True after calling
            `provisionally_link_clinical_indication_to_superpanel` on it
        """

        provisionally_link_clinical_indication_to_superpanel(
            self.first_superpanel,
            self.first_clinical_indication,
            "test",
            self.td_version,
        )  # this is an existing link in db

        self.first_clinical_indication_superpanel.refresh_from_db()

        # test that a release was linked to the ci-panel
        with self.subTest():
            assert self.first_clinical_indication_superpanel.pending

        # test that a release was linked to the ci-superpanel
        with self.subTest():
            releases = TestDirectoryRelease.objects.all()
            assert len(releases) == 1
            assert releases[0].release == "5.0"

    def test_that_new_link_is_flagged(self):
        """
        we test for a new link (not existing in db) -
        self.second_clinical_indication is not linked to self.first_superpanel
        in setup
        `provisionally_link_clinical_indication_to_panel` should create the
        link and flag it for review
        """
        provisionally_link_clinical_indication_to_superpanel(
            self.first_superpanel,
            self.second_clinical_indication,
            "test",
            self.td_version,
        )

        # one new link created
        assert ClinicalIndicationSuperPanel.objects.count() == 2

        new_link = ClinicalIndicationSuperPanel.objects.last()

        # new link should be flagged for review
        assert new_link.pending

        # check that a test directory release was linked
        with self.subTest():
            releases = TestDirectoryRelease.objects.all()
            assert len(releases) == 1
            assert releases[0].release == "5.0"


class TestRetrievePanelFromPanelID(TestCase):
    """
    `_retrieve_panel_from_pa_id` will retrieve a panel from db based on given panel id
    panel id is the external id of a panel

    if there are multiple panel with the same external id, the latest version will be retrieved
    """

    def setUp(self) -> None:
        self.first_panel = Panel.objects.create(
            external_id=123,
            panel_name="Test panel",
            panel_version=sortable_version("1.15"),
        )

        self.second_panel = Panel.objects.create(
            external_id=123,
            panel_name="Test panel",
            panel_version=sortable_version("1.19"),  # notice the version number
        )

    def test_that_latest_panel_version_will_be_retrieved(self):
        """
        Case: Trying to fetch the latest version for a panel which exists in 2 versions
        Expect: The panel with the most-recent version number to be returned
        """
        panel = _retrieve_panel_from_pa_id(123)

        assert panel.panel_version == sortable_version("1.19")

    def test_that_it_will_return_none_if_panel_id_does_not_exist(self):
        """
        Case: Trying to fetch the latest version for a panel which is not in the database
        Expect: Function returns None
        """
        panel = _retrieve_panel_from_pa_id(999)

        assert panel == None


class TestRetrieveUnknownMetadataRecords(TestCase):
    """
    this function is mainly called when we got no idea what
    confidence level, mode of inheritance, mode of pathogenicity and penetrance
    it will simply retrieve or create all those values from db as none
    """

    conf, moi, mop, pen = _retrieve_unknown_metadata_records()

    assert conf.confidence_level == None
    assert moi.mode_of_inheritance == None
    assert mop.mode_of_pathogenicity == None
    assert pen.penetrance == None


class TestMakeProvisionalTestMethodChange(TestCase):
    def setUp(self) -> None:
        self.first_clinical_indication = ClinicalIndication.objects.create(
            r_code="R123", name="Test CI", test_method="Test method"
        )

    def test_if_clinical_indication_is_flagged(self):
        """
        this function is called when a clinical indication's test method changed
        it will make a record in ClinicalIndicationTestMethodHistory model, flag the clinical indication for review
        and update the test method of the clinical indication
        """

        _make_provisional_test_method_change(
            self.first_clinical_indication, "Test method 2", "test user"
        )

        self.first_clinical_indication.refresh_from_db()

        assert (
            self.first_clinical_indication.test_method == "Test method 2"
        )  # test method updated for clinical indication
        assert self.first_clinical_indication.pending == True  # flagged for review

        assert (
            ClinicalIndicationTestMethodHistory.objects.count() == 1
        )  # one history recorded
