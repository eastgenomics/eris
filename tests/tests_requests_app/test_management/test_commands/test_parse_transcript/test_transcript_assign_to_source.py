from django.test import TestCase



from requests_app.management.commands._parse_transcript import (
    _transcript_assign_to_source,
)


class TestTranscriptAssigner_TxAbsent(TestCase):
    """
    CASE: transcript isn't in any resource
    EXPECT the transcript to return as non-clinical
    """

    def test_default_additional_transcript_non_clin(self):
        hgnc_id = "1234"
        tx = "NM00004.1"

        mane_data = []
        markname_hgmd = {}
        gene2refseq_hgmd = {}

        (
            mane_select_data,
            mane_plus_clinical_data,
            hgmd_data,
            err,
        ) = _transcript_assign_to_source(
            tx, hgnc_id, mane_data, markname_hgmd, gene2refseq_hgmd
        )

        no_results = {"clinical": None, "match_base": None, "match_version": None}

        with self.subTest():
            self.assertDictEqual(mane_select_data, no_results)
        with self.subTest():
            self.assertDictEqual(mane_plus_clinical_data, no_results)
        with self.subTest():
            self.assertDictEqual(hgmd_data, no_results)


class TestTranscriptAssigner_InMane(TestCase):
    """
    Tests for scenarios in which the transcript is seen in MANE.
    Includes scenarios where the sources are Select and Plus Clinical,
    and where the matches are exact or versionless
    """

    def test_mane_select_versionless_match(self):
        """
        CASE: gene and/or transcript in MANE Select data, with a versionless match
        EXPECT: the MANE Select data to be filled out as Clinical, with other dicts
        being empty
        """
        hgnc_id = "1234"
        tx = "NM00004.1"

        mane_data = [
            {"HGNC ID": "1234", "RefSeq": "NM00004.2", "MANE TYPE": "MANE SELECT"}
        ]
        markname_hgmd = {}
        gene2refseq_hgmd = {}

        (
            mane_select_data,
            mane_plus_clinical_data,
            hgmd_data,
            err,
        ) = _transcript_assign_to_source(
            tx, hgnc_id, mane_data, markname_hgmd, gene2refseq_hgmd
        )

        # expected values
        mane_select_expected = {
            "clinical": True,
            "match_base": True,
            "match_version": False,
        }
        mane_plus_clinical_expected = {
            "clinical": None,
            "match_base": None,
            "match_version": None,
        }
        hgmd_data_expected = {
            "clinical": None,
            "match_base": None,
            "match_version": None,
        }

        with self.subTest():
            self.assertDictEqual(mane_select_data, mane_select_expected)
        with self.subTest():
            self.assertDictEqual(mane_plus_clinical_data, mane_plus_clinical_expected)
        with self.subTest():
            self.assertDictEqual(hgmd_data, hgmd_data_expected)

    def test_mane_plus_versionless_match(self):
        """
        CASE: gene and/or transcript in MANE Plus Clinical data, with a versionless match
        EXPECT: the MANE Plus Clinical data to be filled out as Clinical, with other dicts
        being empty
        """
        hgnc_id = "1234"
        tx = "NM00004.1"

        mane_data = [
            {
                "HGNC ID": "1234",
                "RefSeq": "NM00004.2",
                "MANE TYPE": "MANE PLUS CLINICAL",
            }
        ]
        markname_hgmd = {}
        gene2refseq_hgmd = {}

        (
            mane_select_data,
            mane_plus_clinical_data,
            hgmd_data,
            err,
        ) = _transcript_assign_to_source(
            tx, hgnc_id, mane_data, markname_hgmd, gene2refseq_hgmd
        )

        # expected values
        mane_plus_clinical_expected = {
            "clinical": True,
            "match_base": True,
            "match_version": False,
        }
        no_data = {"clinical": None, "match_base": None, "match_version": None}

        with self.subTest():
            self.assertDictEqual(mane_select_data, no_data)
        with self.subTest():
            self.assertDictEqual(mane_plus_clinical_data, mane_plus_clinical_expected)
        with self.subTest():
            self.assertDictEqual(hgmd_data, no_data)

    def test_mane_select_versioned_match(self):
        """
        CASE: gene and/or transcript in MANE Select data, with a perfect match
        EXPECT: the MANE Select data to be filled out as Clinical, with other dicts
        being empty
        """
        hgnc_id = "1234"
        tx = "NM00004.1"

        mane_data = [
            {"HGNC ID": "1234", "RefSeq": "NM00004.1", "MANE TYPE": "MANE SELECT"}
        ]
        markname_hgmd = {}
        gene2refseq_hgmd = {}

        (
            mane_select_data,
            mane_plus_clinical_data,
            hgmd_data,
            err,
        ) = _transcript_assign_to_source(
            tx, hgnc_id, mane_data, markname_hgmd, gene2refseq_hgmd
        )

        # expected values
        mane_select_expected = {
            "clinical": True,
            "match_base": True,
            "match_version": True,
        }
        mane_plus_clinical_expected = {
            "clinical": None,
            "match_base": None,
            "match_version": None,
        }
        hgmd_data_expected = {
            "clinical": None,
            "match_base": None,
            "match_version": None,
        }
        with self.subTest():
            self.assertDictEqual(mane_select_data, mane_select_expected)
        with self.subTest():
            self.assertDictEqual(mane_plus_clinical_data, mane_plus_clinical_expected)
        with self.subTest():
            self.assertDictEqual(hgmd_data, hgmd_data_expected)

    def test_mane_plus_versionless_match(self):
        """
        CASE: gene and/or transcript in MANE Plus Clinical data, with a perfect match
        EXPECT: the MANE Plus Clinical data to be filled out as Clinical, with other dicts
        being empty
        """
        hgnc_id = "1234"
        tx = "NM00004.1"

        mane_data = [
            {
                "HGNC ID": "1234",
                "RefSeq": "NM00004.1",
                "MANE TYPE": "MANE PLUS CLINICAL",
            }
        ]
        markname_hgmd = {}
        gene2refseq_hgmd = {}

        (
            mane_select_data,
            mane_plus_clinical_data,
            hgmd_data,
            err,
        ) = _transcript_assign_to_source(
            tx, hgnc_id, mane_data, markname_hgmd, gene2refseq_hgmd
        )

        # expected values
        mane_plus_clinical_expected = {
            "clinical": True,
            "match_base": True,
            "match_version": True,
        }
        no_data = {"clinical": None, "match_base": None, "match_version": None}
        with self.subTest():
            self.assertDictEqual(mane_select_data, no_data)
        with self.subTest():
            self.assertDictEqual(mane_plus_clinical_data, mane_plus_clinical_expected)
        with self.subTest():
            self.assertDictEqual(hgmd_data, no_data)


class TestTranscriptAssigner_InHgmd(TestCase):
    """
    Tests for scenarios where the transcript is present in HGMD.
    Because the logic for finding the transcript name in HGME is primarily
    handled by a different function, we mock a lot of this.
    """

    def test_gene_transcript_in_hgmd(self):
        """
        CASE: Transcript is in HGMD
        EXPECT: Transcript info for HGMD will be filled in
        """
        hgnc_id = "HGNC:1234"
        tx = "NM00004.1"

        mane_data = []
        markname_hgmd = {"1234": ["test"]}
        gene2refseq_hgmd = {"test": [["NM00004", "1"]]}

        (
            mane_select_data,
            mane_plus_clinical_data,
            hgmd_data,
            err,
        ) = _transcript_assign_to_source(
            tx, hgnc_id, mane_data, markname_hgmd, gene2refseq_hgmd
        )

        # expected values
        hgmd_expected = {"clinical": True, "match_base": True, "match_version": False}
        no_data = {"clinical": None, "match_base": None, "match_version": None}

        with self.subTest():
            self.assertDictEqual(mane_select_data, no_data)
        with self.subTest():
            self.assertDictEqual(mane_plus_clinical_data, no_data)
        with self.subTest():
            self.assertDictEqual(hgmd_data, hgmd_expected)

    def test_gene_transcript_not_in_hgmd(self):
        """
        CASE: Transcript is not in HGMD
        EXPECT: Transcript info for HGMD will be default
        """
        hgnc_id = "HGNC:1234"
        tx = "NM00004.1"

        mane_data = []
        markname_hgmd = {"1234": ["test"]}
        gene2refseq_hgmd = {"test": [["NM00010", "1"]]}

        (
            mane_select_data,
            mane_plus_clinical_data,
            hgmd_data,
            err,
        ) = _transcript_assign_to_source(
            tx, hgnc_id, mane_data, markname_hgmd, gene2refseq_hgmd
        )

        # expected values
        no_data = {"clinical": None, "match_base": None, "match_version": None}

        with self.subTest():
            self.assertDictEqual(mane_select_data, no_data)
        with self.subTest():
            self.assertDictEqual(mane_plus_clinical_data, no_data)
        with self.subTest():
            self.assertDictEqual(hgmd_data, no_data)
