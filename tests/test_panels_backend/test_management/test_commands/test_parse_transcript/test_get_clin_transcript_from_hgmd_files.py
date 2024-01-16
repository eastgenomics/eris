from django.test import TestCase

import numpy as np


from panels_backend.management.commands._parse_transcript import (
    _get_clin_transcript_from_hgmd_files,
)


class TestHgmdFileFetcher_ErrorStates(TestCase):
    """
    Tests for _get_clin_transcript_from_hgmd_files, focusing
    on catching possible error states.
    """

    def test_short_hgnc_not_in_markname(self):
        """
        Test that if a gene ID isn't in the markname HGMD table,
        an error is returned.
        """
        hgnc_id = "HGNC:1234"
        markname = {"1235": ["5678"]}  # doesn't match the HGNC_ID
        gene2refseq = {}

        result, test_error = _get_clin_transcript_from_hgmd_files(
            hgnc_id, markname, gene2refseq
        )

        expected_err = "HGNC:1234 not found in markname HGMD table"

        assert not result
        assert test_error == expected_err

    def test_markname_multiple_entries(self):
        """
        Test that if a gene ID has several entries in the markname HGMD table,
        an error is returned.
        """
        hgnc_id = "HGNC:1234"
        markname = {"1234": ["5678", "9101"]}
        gene2refseq = {}

        result, test_error = _get_clin_transcript_from_hgmd_files(
            hgnc_id, markname, gene2refseq
        )

        expected_err = "HGNC:1234 has two or more entries in markname HGMD table."

        assert not result
        assert test_error == expected_err

    def test_markname_gene_id_blank_string(self):
        """
        Test that if a gene ID has a blank ID in the markname HGMD table,
        an error is returned.
        """
        hgnc_id = "HGNC:1234"
        markname = {"1234": []}
        gene2refseq = {}

        result, test_error = _get_clin_transcript_from_hgmd_files(
            hgnc_id, markname, gene2refseq
        )

        expected_err = "HGNC:1234 has no gene_id in markname table"

        assert not result
        assert test_error == expected_err

    def test_markname_gene_id_nonetype(self):
        """
        Test that if a gene ID has a None entry in the markname HGMD table,
        an error is returned.
        """
        hgnc_id = "HGNC:1234"
        markname = {"1234": [None]}
        gene2refseq = {}

        result, test_error = _get_clin_transcript_from_hgmd_files(
            hgnc_id, markname, gene2refseq
        )

        expected_err = "HGNC:1234 has no gene_id in markname table"

        assert not result
        assert test_error == expected_err

    def test_markname_gene_id_nantype(self):
        """
        Test that if a gene ID has an np.nan entry in the markname HGMD table,
        an error is returned.
        """
        hgnc_id = "HGNC:1234"
        markname = {"1234": [np.nan]}
        gene2refseq = {}

        result, test_error = _get_clin_transcript_from_hgmd_files(
            hgnc_id, markname, gene2refseq
        )

        assert not result
        expected_err = "HGNC:1234 has no gene_id in markname table"

        assert test_error == expected_err

    def test_gene2refseq_lacks_gene_id(self):
        """
        Test that if a gene's HGMD-markname ID isn't in the gene2refseq table,
        an error is returned.
        """
        hgnc_id = "HGNC:1234"
        markname = {"1234": ["5678"]}
        gene2refseq = {}

        result, test_error = _get_clin_transcript_from_hgmd_files(
            hgnc_id, markname, gene2refseq
        )

        expected_err = "HGNC:1234 with gene id 5678 not in gene2refseq table"

        assert not result
        assert test_error == expected_err

    def test_gene2reqseq_entry_contains_list_of_lists(self):
        """
        CASE: A gene's HGMD-markname ID has several transcript entries in the gene2refseq table
        EXPECT: An error is returned.
        """
        hgnc_id = "HGNC:1234"
        markname = {"1234": ["5678"]}
        gene2refseq = {"5678": [["NM005", "1"], ["NM009", "1"]]}

        result, test_error = _get_clin_transcript_from_hgmd_files(
            hgnc_id, markname, gene2refseq
        )

        expected_err = (
            "HGNC:1234 has more than one transcript in the HGMD database: NM005,NM009"
        )

        assert not result
        assert test_error == expected_err

    def test_gene2reqseq_entry_is_valid(self):
        """
        CASE: All of the input is valid
        EXPECT: Returns the correct transcript in HGMD, for this particular HGNC_ID
        """
        hgnc_id = "HGNC:1234"
        markname = {"1234": ["5678"]}
        gene2refseq = {"5678": [["NM005", "1"]]}

        result, test_error = _get_clin_transcript_from_hgmd_files(
            hgnc_id, markname, gene2refseq
        )

        expected_err = None

        assert result == "NM005"
        assert test_error == expected_err
