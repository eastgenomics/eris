from django.test import TestCase

import numpy as np


from requests_app.management.commands._parse_transcript import \
    _get_clin_transcript_from_hgmd_files


class TestHgmdFileFetcher_ErrorStates(TestCase):
    def test_short_hgnc_not_in_markname(self):
        hgnc_id = "HGNC:1234"
        markname = {"not_1234": ["5678"]}
        gene2refseq = {}

        result, test_error = _get_clin_transcript_from_hgmd_files(hgnc_id, markname, 
                                                                  gene2refseq)

        expected_err = "HGNC:1234 not found in markname HGMD table"

        assert test_error == expected_err

    def test_markname_multiple_entries(self):
        hgnc_id = "HGNC:1234"
        markname = {"1234": ["5678", "9101"]}
        gene2refseq = {}

        result, test_error = _get_clin_transcript_from_hgmd_files(hgnc_id, markname, 
                                                                  gene2refseq)

        expected_err = "HGNC:1234 has two or more entries in markname HGMD table."

        assert test_error == expected_err
        
    def test_markname_gene_id_blank_string(self):
        hgnc_id = "HGNC:1234"
        markname = {"1234": [""]}
        gene2refseq = {}

        result, test_error = _get_clin_transcript_from_hgmd_files(hgnc_id, markname, 
                                                                  gene2refseq)

        expected_err = "HGNC:1234 has no gene_id in markname table"

        assert test_error == expected_err

    def test_markname_gene_id_nonetype(self):
        hgnc_id = "HGNC:1234"
        markname = {"1234": [None]}
        gene2refseq = {}

        result, test_error = _get_clin_transcript_from_hgmd_files(hgnc_id, markname, 
                                                                  gene2refseq)

        expected_err = "HGNC:1234 has no gene_id in markname table"

        assert test_error == expected_err

    def test_markname_gene_id_nantype(self):
        hgnc_id = "HGNC:1234"
        markname = {"1234": [np.nan]}
        gene2refseq = {}

        result, test_error = _get_clin_transcript_from_hgmd_files(hgnc_id, markname, 
                                                                  gene2refseq)

        expected_err = "HGNC:1234 has no gene_id in markname table"

        assert test_error == expected_err

    def test_gene2refseq_lacks_gene_id(self):
        hgnc_id = "HGNC:1234"
        markname = {"1234": ["5678"]}
        gene2refseq = {}

        result, test_error = _get_clin_transcript_from_hgmd_files(hgnc_id, markname, 
                                                                  gene2refseq)

        expected_err = "HGNC:1234 with gene id 5678 not in gene2refseq table"

        assert test_error == expected_err
    
    def test_gene2reqseq_entry_contains_list_of_lists(self):
        hgnc_id = "HGNC:1234"
        markname = {"1234": ["5678"]}
        gene2refseq = {"5678": [["NM005", "1"], ["NM009", "1"]]}

        result, test_error = _get_clin_transcript_from_hgmd_files(hgnc_id, markname, 
                                                                  gene2refseq)

        expected_err = \
            "HGNC:1234 has more than one transcript in the HGMD database: NM005,NM009"

        assert test_error == expected_err

# For passing states, see the tests for the parent function, _transcript_assigner
