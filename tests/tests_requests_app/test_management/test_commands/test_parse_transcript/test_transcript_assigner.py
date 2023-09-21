from django.test import TestCase

import pandas as pd


from requests_app.management.commands._parse_transcript import \
    _transcript_assigner


class TestTranscriptAssigner_AlreadyAdded(TestCase):
    """
    CASE: gene and transcript are in gene_clinical_transcript already
    EXPECT the transcript to return as non-clinical
    """
    #TODO: work out when and where to split the transcript down to base
    def test_default_additional_transcript_non_clin(self):

        hgnc_id = "1234"
        tx = "NM00004.1"
        gene_clinical_transcript = {"1234": ["NM00008.1", "MANE"]}

        mane_data = {}
        markname_hgmd = {}
        gene2refseq_hgmd = {}

        clinical, source, err = _transcript_assigner(tx, hgnc_id, gene_clinical_transcript, 
                         mane_data, markname_hgmd, gene2refseq_hgmd)

        assert not clinical
        assert not source
        assert not err


class TestTranscriptAssigner_InMane(TestCase):
    """
    # CASE gene and/or transcript in MANE data
    """
    def test_gene_transcript_in_mane(self):
        # EXPECT the transcript to return straight away as clinical, source = MANE,
        # regardless of whether it's in other files or not
        hgnc_id = "1234"
        tx = "NM00004.1"
        gene_clinical_transcript = {}

        mane_data = {"1234": "NM00004.2"}
        markname_hgmd = {}
        gene2refseq_hgmd = {}

        clinical, source, err = _transcript_assigner(tx, hgnc_id, gene_clinical_transcript, 
                         mane_data, markname_hgmd, gene2refseq_hgmd)

        assert clinical
        assert source == "MANE"
        assert not err


#TODO: transcript assigner cases: