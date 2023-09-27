from django.test import TestCase


from requests_app.models import \
    Gene, Transcript


from requests_app.management.commands._parse_transcript import \
    _add_gene_and_transcript_to_db
from ..test_insert_panel.test_insert_gene import len_check_wrapper, value_check_wrapper


class TestAddGeneTranscript_FromScratch(TestCase):
    """
    Cases where transcripts and genes are being added to a 'clean' 
    database with no entries - emulates situations where the gene 
    and transcript aren't already in the database, have old 
    versions that need handling, and so on.

    One case is for when a gene has 1 transcript,
    another is for multiple transcripts.
    """
    def setUp(self) -> None:
        return super().setUp()
    
    def test_add_new_gene_new_transcript_single(self):
        """
        Straightforward use case, one transcript per gene
        """
        err = []

        hgnc_id = "HGNC:0001"
        transcripts = ["NM00045.6"]
        reference = ""
        source = "MANE"

        _add_gene_and_transcript_to_db(hgnc_id, transcripts, reference, source)

        new_genes = Gene.objects.all()
        new_transcripts = Transcript.objects.all()

        # Check that the expected values were added to the database
        err += len_check_wrapper(new_genes, "gene", 1)
        err += value_check_wrapper(new_genes[0].hgnc_id, "gene HGNC", "HGNC:0001")
        err += value_check_wrapper(new_genes[0].gene_symbol, "gene symbol", None)

        err += len_check_wrapper(new_transcripts, "transcript", 1)
        err += value_check_wrapper(new_transcripts[0].transcript, "transcript name", "NM00045.6")
        err += value_check_wrapper(new_transcripts[0].source, "source", "MANE")
        err += value_check_wrapper(new_transcripts[0].reference_genome, "ref", "")

        errors = "; ".join(err)
        assert not errors, errors


    def test_add_new_gene_new_transcript_multiple(self):
        """
        Straightforward case, but with multiple transcripts
        """
        err = []

        hgnc_id = "HGNC:0001"
        transcripts = ["NM00045.6", "NM00800.1"]
        reference = ""
        source = None

        _add_gene_and_transcript_to_db(hgnc_id, transcripts, reference, source)


        new_genes = Gene.objects.all()
        new_transcripts = Transcript.objects.all()

        # Check that the expected values were added to the database
        err += len_check_wrapper(new_genes, "gene", 1)
        err += value_check_wrapper(new_genes[0].hgnc_id, "gene HGNC", "HGNC:0001")
        err += value_check_wrapper(new_genes[0].gene_symbol, "gene symbol", None)

        err += len_check_wrapper(new_transcripts, "transcript", 2)
        first = new_transcripts[0]
        second = new_transcripts[1]
        err += value_check_wrapper(first.transcript, "transcript name", "NM00045.6")
        err += value_check_wrapper(first.source, "source", None)
        err += value_check_wrapper(first.reference_genome, "ref", "")
        err += value_check_wrapper(second.transcript, "transcript name", "NM00800.1")
        err += value_check_wrapper(second.source, "source", None)
        err += value_check_wrapper(second.reference_genome, "ref", "")

        errors = "; ".join(err)
        assert not errors, errors


class TestAddGeneTranscript_AlreadyExists(TestCase):
    """
    Cases where transcripts are being added to a database which
    already contains a gene and transcript.

    Testing transcripts are still created if they are different in e.g. their reference version 
    or source, from an already-existing transcript.

    #TODO: needs development - as part of plans to implement a more informative
    versioning system for transcripts.
    """

    def setUp(self) -> None:
        self.start_gene = Gene.objects.create(
            hgnc_id="HGNC:0001"
        )

        self.start_transcript = Transcript.objects.get_or_create(
            transcript="NM00045.6",
            source="MANE",
            gene_id=self.start_gene.pk,
            reference_genome="37"
        )
    

    def test_add_old_gene_changed_transcript(self):
        err = []

        hgnc_id = "HGNC:0001"
        transcripts = ["NM00045.6"]
        reference = "38"
        source = None

        _add_gene_and_transcript_to_db(hgnc_id, transcripts, reference, source)

        all_transcripts = Transcript.objects.all()

        # expect old and new copy for the same transcript
        err += len_check_wrapper(all_transcripts, "transcript", 2)
        new_tx = all_transcripts[1]
        err += value_check_wrapper(new_tx.transcript, "transcript name", "NM00045.6")
        err += value_check_wrapper(new_tx.source, "source", None)
        err += value_check_wrapper(new_tx.reference_genome, "ref", "38")

        errors = "; ".join(err)
        assert not errors, errors
