from django.test import TestCase

from requests_app.models import (
    TestDirectoryRelease,
)
from requests_app.management.commands._insert_ci import _fetch_latest_td_version


class TestFetchLatestTdVersion_FullDb(TestCase):
    """
    CASE: Database contains td releases
    EXPECT: Highest td version is returned correctly
    """

    def setUp(self) -> None:
        self.td_release = TestDirectoryRelease.objects.create(release="2")

        self.td_release_two = TestDirectoryRelease.objects.create(release="3.0.0")

        self.td_release_three = TestDirectoryRelease.objects.create(release="3.0.1")

    def test_highest_returned(self):
        """
        CASE: Database contains td releases
        EXPECT: Highest td version is returned correctly
        """
        latest_td = _fetch_latest_td_version()

        assert latest_td == "3.0.1"


class TestFetchLatestTdVersion_NoDataAvailable(TestCase):
    """
    CASE: There is no data in the db
    EXPECT: td version returns as None
    """

    def setUp(self) -> None:
        pass

    def test_only_panel_exists(self):
        latest_td = _fetch_latest_td_version()

        assert not latest_td
