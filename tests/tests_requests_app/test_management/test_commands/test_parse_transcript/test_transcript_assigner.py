from django.test import TestCase

import pandas as pd


from requests_app.management.commands._parse_transcript import _transcript_assigner


class TestTranscriptAssigner_AlreadyAdded(TestCase):
    """
    CASE: gene and transcript are in gene_clinical_transcript already
    EXPECT the transcript to return as non-clinical
    """

    def test_default_additional_transcript_non_clin(self):
        hgnc_id = "1234"
        tx = "NM00004.1"
        gene_clinical_transcript = {"1234": ["NM00008.1", "MANE"]}

        mane_data = {}
        markname_hgmd = {}
        gene2refseq_hgmd = {}

        clinical, source, err = _transcript_assigner(
            tx,
            hgnc_id,
            gene_clinical_transcript,
            mane_data,
            markname_hgmd,
            gene2refseq_hgmd,
        )

        errors = [x for x in [clinical, source, err] if x]

        assert not errors, errors


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

        clinical, source, err = _transcript_assigner(
            tx,
            hgnc_id,
            gene_clinical_transcript,
            mane_data,
            markname_hgmd,
            gene2refseq_hgmd,
        )

        errors = [x for x in [clinical, source == "MANE", not err] if not x]

        assert not errors, errors


class TestTranscriptAssigner_GeneInHgmd(TestCase):
    """
    CASE testing presence/absence in HGMD
    """

    def test_gene_transcript_in_hgmd(self):
        # Transcript in HGMD matches the transcript we're currently feeding to the function
        # Expect it to be tagged clinical with 'HGMD' as source
        hgnc_id = "HGNC:1234"
        tx = "NM00004.1"
        gene_clinical_transcript = {}

        mane_data = {}
        markname_hgmd = {"1234": ["test"]}
        gene2refseq_hgmd = {"test": [["NM00004", "1"]]}

        clinical, source, err = _transcript_assigner(
            tx,
            hgnc_id,
            gene_clinical_transcript,
            mane_data,
            markname_hgmd,
            gene2refseq_hgmd,
        )

        errors = [x for x in [clinical, source == "HGMD", not err] if not x]

        assert not errors, errors

    def test_gene_in_hgmd_but_transcript_wrong(self):
        # The gene is in HGMD, but the transcript in HGMD does not match our current input
        # Expect it to be left as non-clinical with None source
        hgnc_id = "HGNC:1234"
        tx = "NM10.1"
        gene_clinical_transcript = {}

        mane_data = {}
        markname_hgmd = {"1234": ["1"]}
        gene2refseq_hgmd = {"1": [["NM00004", "2"]]}

        clinical, source, err = _transcript_assigner(
            tx,
            hgnc_id,
            gene_clinical_transcript,
            mane_data,
            markname_hgmd,
            gene2refseq_hgmd,
        )

        errors = [x for x in [clinical, source, err] if x]

        assert not errors, errors
