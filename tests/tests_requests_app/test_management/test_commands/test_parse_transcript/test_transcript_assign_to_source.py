# from django.test import TestCase

# import pandas as pd


# from requests_app.management.commands._parse_transcript import \
#     _transcript_assign_to_source

#TODO: these all need rewriting

# class TestTranscriptAssigner_AlreadyAdded(TestCase):
#     """
#     CASE: gene and transcript are in gene_clinical_transcript already
#     EXPECT the transcript to return as non-clinical
#     """
#     def test_default_additional_transcript_non_clin(self):

#         hgnc_id = "1234"
#         tx = "NM00004.1"

#         mane_data = pd.DataFrame()
#         markname_hgmd = {}
#         gene2refseq_hgmd = {}
# mane_select_data, mane_plus_clinical_data, hgmd_data, err
#         clinical, source, err = _transcript_assign_to_source(tx, hgnc_id,  
#                                                      mane_data, markname_hgmd, 
#                                                      gene2refseq_hgmd)
        
#         errors = [x for x in [clinical, source, err] if x]

#         assert not errors, errors


# class TestTranscriptAssigner_InMane(TestCase):
#     """
#     # CASE gene and/or transcript in MANE data
#     """
#     def test_gene_transcript_in_mane(self):
#         # EXPECT the transcript to return straight away as clinical, source = MANE,
#         # regardless of whether it's in other files or not
#         hgnc_id = "1234"
#         tx = "NM00004.1"

#         mane_data = pd.DataFrame({
#          "HGNC_ID": pd.Series("1234"),
#          "RefSeq StableID GRCh38 / GRCh37": pd.Series(["NM00004.2"]),
#          "MANE TYPE": pd.Series(),
#          "Gene": pd.Series()
#         })
#         markname_hgmd = {}
#         gene2refseq_hgmd = {}

#         clinical, source, err = _transcript_assign_to_source(tx,
#                                                      hgnc_id,
#                                                      mane_data,
#                                                      markname_hgmd,
#                                                      gene2refseq_hgmd)

#         errors = [x for x in [clinical, source == "MANE", not err] if not x]

#         assert not errors, errors


# class TestTranscriptAssigner_GeneInHgmd(TestCase):
#     """
#     CASE testing presence/absence in HGMD
#     """
#     def test_gene_transcript_in_hgmd(self):
#         # Transcript in HGMD matches the transcript we're currently feeding to the function
#         # Expect it to be tagged clinical with 'HGMD' as source
#         hgnc_id = "HGNC:1234"
#         tx = "NM00004.1"

#         mane_data = pd.DataFrame()
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

#         mane_data = pd.DataFrame()
#         markname_hgmd = {"1234": ["1"]}
#         gene2refseq_hgmd = {"1": [["NM00004", "2"]]}

#         clinical, source, err = _transcript_assign_to_source(tx,
#                                                      hgnc_id,
#                                                      mane_data,
#                                                      markname_hgmd,
#                                                      gene2refseq_hgmd)

#         errors = [x for x in [clinical, source, err] if x]

#         assert not errors, errors
