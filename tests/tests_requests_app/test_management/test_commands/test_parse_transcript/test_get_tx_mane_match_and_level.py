from django.test import TestCase

from requests_app.management.commands.tx_match import MatchType
from requests_app.management.commands._parse_transcript import \
    _get_tx_mane_match_and_level
from ..test_insert_panel.test_insert_gene import len_check_wrapper, value_check_wrapper


class TestGetTxMatchAndLevel(TestCase):
    """
    Check that the function can assign match types,
    exact or versionless
    """
    def test_exact_match(self):
        """
        If there's an exact match for the transcript including its version,
        we expect the test to return the currently-added release and
        mark the transcript as a 'complete match'
        """
        tx_mane_release = [
            {
                "tx": "NM0001.3",
                "tx_base": "NM0001",
                "tx_version": "3",
                "mane_release": "Release_5"
            }
        ]

        tx = "NM0001.3"

        release, match_type = _get_tx_mane_match_and_level(tx_mane_release, tx)

        assert release == "Release_5"
        assert match_type == MatchType.complete_match()

    def test_versionless_match(self):
        """
        If there's a match for the transcript only when the version is left off,
        we expect the test to return the currently-added release and
        mark the transcript as a 'versionless match only'
        """
        tx_mane_release = [
            {
                "tx": "NM0001.5", #note higher version number than our test tx
                "tx_base": "NM0001",
                "tx_version": "3",
                "mane_release": "Release_5"
            }
        ]

        tx = "NM0001.3"

        release, match_type = _get_tx_mane_match_and_level(tx_mane_release, tx)

        assert release == "Release_5"
        assert match_type == MatchType.versionless_match_only()

    def test_no_match(self):
        """
        If the transcript isn't represented at all, we expect the
        test to return None for release version and match type.
        """
        tx_mane_release = [
            {
                "tx": "NM0001.5", #note this transcript is fully different from tx
                "tx_base": "NM0001",
                "tx_version": "3",
                "mane_release": "Release_5"
            }
        ]

        tx = "NM1234.5"

        release, match_type = _get_tx_mane_match_and_level(tx_mane_release, tx)

        assert release == None
        assert match_type == None
