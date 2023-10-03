from django.test import TestCase


from requests_app.models import \
    Gene, Transcript, TranscriptSource


from requests_app.management.commands._parse_transcript import \
    _add_non_clinical_gene_and_transcript_to_db
from ..test_insert_panel.test_insert_gene import len_check_wrapper, value_check_wrapper


class TestNonClinicalGene_FromScratch(TestCase):
    """
    Testing that straightforward use of the function works fine:
    creating a gene and its transcripts from scratch.
    """
    def test_from_scratch(self):
        """
        Case: Add 2 transcripts to a new gene
        """
        err = []

        hgnc_id = "HGNC:001"
        transcripts = ["NM001.2", "NM003.2"]
        reference_genome = "37"
        
        _add_non_clinical_gene_and_transcript_to_db(hgnc_id, transcripts,
                                                    reference_genome)
        
        genes = Gene.objects.all()
        transcripts = Transcript.objects.all()

        err += len_check_wrapper(genes, "genes", 1)
        err += len_check_wrapper(transcripts, "tx", 2)
        first_tx = transcripts[0]
        second_tx = transcripts[1]
        err += value_check_wrapper(first_tx.transcript, "tx", "NM001.2")
        err += value_check_wrapper(second_tx.transcript, "tx", "NM003.2")

        errors = "; ".join(err)
        assert not errors, errors


class TestNonClinicalGene_AlreadyExists(TestCase):
    """
    Cases where transcripts are being added to a database which
    already contains its gene and a transcript.

    The second transcript will be added. Most of the time this is
    NOT desired behaviour, however, it may be in some circumstances
    (e.g. 37 having a different transcript from 38)
    """

    def setUp(self) -> None:
        self.start_gene = Gene.objects.create(
            hgnc_id="HGNC:0001"
        )

        self.start_transcript = Transcript.objects.get_or_create(
            transcript="NM001.2",
            gene=self.start_gene,
            reference_genome="37"
        )
    
        
    def test_gene_exists_already(self):
        """
        Case: Add 2 transcripts to a new gene. One tx already
        exists so it doesn't get re-added, the second is new
        and is added.
        """
        err = []

        hgnc_id = "HGNC:0001"
        transcripts = ["NM001.2", "NM003.2"]
        reference_genome = "37"
        
        _add_non_clinical_gene_and_transcript_to_db(hgnc_id, transcripts,
                                                    reference_genome)
        
        genes = Gene.objects.all()
        transcripts = Transcript.objects.all()

        err += len_check_wrapper(genes, "genes", 1)
        err += len_check_wrapper(transcripts, "tx", 2)
        first_tx = transcripts[0]
        second_tx = transcripts[1]
        err += value_check_wrapper(first_tx.transcript, "tx", "NM001.2")
        err += value_check_wrapper(second_tx.transcript, "tx", "NM003.2")

        errors = "; ".join(err)
        assert not errors, errors
