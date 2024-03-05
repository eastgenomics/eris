from django.test import TestCase


from panels_backend.models import (
    TranscriptRelease,
    TranscriptSource,
    ReferenceGenome,
)
from panels_backend.management.commands._parse_transcript import (
    _get_highest_mane_version,
)


class TestHighestMane(TestCase):
    def setUp(self) -> None:
        """
        Set up MANE sources and ref genome
        """
        self.mane_select = TranscriptSource.objects.create(
            source="MANE Select"
        )

        self.mane_plus_clinical = TranscriptSource.objects.create(
            source="MANE Plus Clinical"
        )

        self.grch37 = ReferenceGenome.objects.create(name="GRCh37")

    def test_both_none(self):
        """
        CASE: There's no already-existing db entry for MANE Select or MANE
        Plus Clinical
        EXPECT: Return None
        """
        select = None
        plus = None
        max_mane = _get_highest_mane_version(select, plus)
        assert not max_mane

    def test_mane_select_only(self):
        """
        CASE: There's an already-existing db entry for MANE Select, but not
         for MANE Plus Clinical
        EXPECT: Return MANE Select option
        """
        select = TranscriptRelease.objects.create(
            source=self.mane_select, release="3", reference_genome=self.grch37
        )
        plus = None
        max_mane = _get_highest_mane_version(select, plus)
        assert max_mane == "3"

    def test_mane_plus_only(self):
        """
        CASE: There's an already-existing db entry for MANE Plus Clinical, but
         not for MANE Select
        EXPECT: Return MANE Plus Clinical option
        """
        select = None
        plus = TranscriptRelease.objects.create(
            source=self.mane_plus_clinical,
            release="2",
            reference_genome=self.grch37,
        )
        max_mane = _get_highest_mane_version(select, plus)
        assert max_mane == "2"

    def test_both_have_different_versions(self):
        """
        CASE: There are already-existing db entries for MANE Plus Clinical
        and for MANE Select. They are each different
        EXPECT: Return whichever is highest - in this case, MANE Plus Clinical
        """
        select = TranscriptRelease.objects.create(
            source=self.mane_select, release="4", reference_genome=self.grch37
        )
        plus = TranscriptRelease.objects.create(
            source=self.mane_plus_clinical,
            release="5",
            reference_genome=self.grch37,
        )
        max_mane = _get_highest_mane_version(select, plus)
        assert max_mane == "5"

    def test_both_have_different_versions(self):
        """
        CASE: There are already-existing db entries for MANE Plus Clinical
        and for MANE Select. They are the same for each
        EXPECT: Return the shared version
        """
        select = TranscriptRelease.objects.create(
            source=self.mane_select, release="5", reference_genome=self.grch37
        )
        plus = TranscriptRelease.objects.create(
            source=self.mane_plus_clinical,
            release="5",
            reference_genome=self.grch37,
        )
        max_mane = _get_highest_mane_version(select, plus)
        assert max_mane == "5"
