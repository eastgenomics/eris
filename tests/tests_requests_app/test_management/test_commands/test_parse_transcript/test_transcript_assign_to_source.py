from django.test import TestCase

import pandas as pd


from requests_app.management.commands._parse_transcript import \
    _transcript_assign_to_source

class TestTranscriptAssigner_AlreadyAdded(TestCase):
    """
    CASE: gene and transcript are in gene_clinical_transcript already
    EXPECT the transcript to return as non-clinical
    """
    def test_default_additional_transcript_non_clin(self):
        hgnc_id = "1234"
        tx = "NM00004.1"

        mane_data = []
        markname_hgmd = {}
        gene2refseq_hgmd = {}
        
        mane_select_data, mane_plus_clinical_data, hgmd_data, err = \
            _transcript_assign_to_source(tx, hgnc_id, mane_data, markname_hgmd,
                                         gene2refseq_hgmd)
        
        no_results = {"clinical": None, "match_base": None,
                        "match_version": None}

        self.assertDictEqual(mane_select_data, no_results)
        self.assertDictEqual(mane_plus_clinical_data, no_results)
        self.assertDictEqual(hgmd_data, no_results)


class TestTranscriptAssigner_InMane(TestCase):
    """
    Tests for scenarios in which the transcript is seen in MANE.
    Includes scenarios where the sources are Select and Plus Clinical,
    and where the matches are exact or versionless
    """
    def test_gene_transcript_in_mane_select_versionless_match(self):
        """
        CASE: gene and/or transcript in MANE Select data, with a versionless match
        EXPECT: the MANE Select data to be filled out as Clinical, with other dicts
        being empty
        """
        hgnc_id = "1234"
        tx = "NM00004.1"

        mane_data = [
            {"HGNC ID": "1234",
             "RefSeq": "NM00004.2",
             "MANE TYPE": "MANE SELECT"}
        ]
        markname_hgmd = {}
        gene2refseq_hgmd = {}

        mane_select_data, mane_plus_clinical_data, hgmd_data, err = \
            _transcript_assign_to_source(tx, hgnc_id, mane_data, markname_hgmd,
                                         gene2refseq_hgmd)

        # expected values
        mane_select_expected = {"clinical": True, "match_base": True,
                        "match_version": False}
        mane_plus_clinical_expected = {"clinical": None, "match_base": None,
                               "match_version": None}
        hgmd_data_expected = {"clinical": None, "match_base": None, "match_version": None}

        self.assertDictEqual(mane_select_data, mane_select_expected)
        self.assertDictEqual(mane_plus_clinical_data, mane_plus_clinical_expected)
        self.assertDictEqual(hgmd_data, hgmd_data_expected) 

# TODO: rewrites for HGMD
# class TestTranscriptAssigner_GeneInHgmd(TestCase):
#     """
#     CASE testing presence/absence in HGMD
#     """
#     def test_gene_transcript_in_hgmd(self):
#         # Transcript in HGMD matches the transcript we're currently feeding to the function
#         # Expect it to be tagged clinical with 'HGMD' as source
#         hgnc_id = "HGNC:1234"
#         tx = "NM00004.1"

#         mane_data = []
#         markname_hgmd = {"1234": ["test"]}
#         gene2refseq_hgmd = {"test": [["NM00004", "1"]]}

#         clinical, source, err = _transcript_assign_to_source(tx,
#                                                      hgnc_id,
#                                                      mane_data,
#                                                      markname_hgmd,
#                                                      gene2refseq_hgmd)

#         errors = [x for x in [clinical, source == "HGMD", not err] if not x]

#         assert not errors, errors

#     def test_gene_in_hgmd_but_transcript_wrong(self):
#         # The gene is in HGMD, but the transcript in HGMD does not match our current input
#         # Expect it to be left as non-clinical with None source
#         hgnc_id = "HGNC:1234"
#         tx = "NM10.1"

#         mane_data = []
#         markname_hgmd = [{"1234": ["1"]}]
#         gene2refseq_hgmd = {"1": [["NM00004", "2"]]}

#         clinical, source, err = _transcript_assign_to_source(tx,
#                                                      hgnc_id,
#                                                      mane_data,
#                                                      markname_hgmd,
#                                                      gene2refseq_hgmd)

#         errors = [x for x in [clinical, source, err] if x]

#         assert not errors, errors
