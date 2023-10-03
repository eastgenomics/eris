from django.test import TestCase


from requests_app.models import \
    Gene, Transcript, TranscriptSource


from requests_app.management.commands._parse_transcript import \
    _add_clinical_gene_and_transcript_to_db
from ..test_insert_panel.test_insert_gene import len_check_wrapper, value_check_wrapper


class TestAddClinicalGeneTranscript_FromScratch(TestCase):
    """
    Cases where transcripts and genes are being added to a 'clean' 
    database with no entries - emulates situations where the gene 
    and transcript aren't already in the database, have old 
    versions that need handling, and so on.
    """
    def setUp(self) -> None:
        return super().setUp()
    
    def test_add_new_gene_new_transcript_single(self):
        """
        Straightforward use case, one transcript per gene
        """
        err = []

        hgnc_id = "HGNC:0001"
        transcript = "NM00045.6"
        reference = "37"
        source = "MANE"
        hgmd_release_label = "release_2"
        tx_mane_release = [
            {
                "tx": "NM00045.6",
                "tx_base": "NM00045",
                "tx_version": "6",
                "mane_release": "release_2"
            }
        ]
        mane_ext_id = "file-123"
        mane_ftp_ext_id = "file-234"
        g2refseq_ext_id = "file-345"
        markname_ext_id = "file-456"

        _add_clinical_gene_and_transcript_to_db(hgnc_id, transcript, reference, source,
                                                hgmd_release_label, tx_mane_release, mane_ext_id,
                                                mane_ftp_ext_id, g2refseq_ext_id, markname_ext_id)

        new_genes = Gene.objects.all()
        new_sources = TranscriptSource.objects.all()
        new_transcripts = Transcript.objects.all()

        # Check that the expected genes were added to the database
        err += len_check_wrapper(new_genes, "gene", 1)
        err += value_check_wrapper(new_genes[0].hgnc_id, "gene HGNC", "HGNC:0001")
        err += value_check_wrapper(new_genes[0].gene_symbol, "gene symbol", None)

        # Check that the sources were added
        err += len_check_wrapper(new_sources, "tx source", 1)
        err += value_check_wrapper(new_sources[0].source, "tx source", "MANE")

        # Check that the transcripts were added
        err += len_check_wrapper(new_transcripts, "transcript", 1)
        err += value_check_wrapper(new_transcripts[0].transcript, "transcript name", "NM00045.6")
        err += value_check_wrapper(new_transcripts[0].reference_genome, "ref", "37")

        errors = "; ".join(err)
        assert not errors, errors


class TestAddGeneTranscript_AlreadyExists(TestCase):
    """
    Cases where transcripts are being added to a database which
    already contains a gene and transcript.

    The second transcript will be added. Most of the time this is
    NOT desired behaviour, however, it may be in some circumstances
    (e.g. 37 having a different transcript from 38)
    """

    def setUp(self) -> None:
        self.start_tx_mane_source = TranscriptSource.objects.get_or_create(
            source="MANE"
        )

        self.start_tx_hgmd_source = TranscriptSource.objects.get_or_create(
            source="HGMD"
        )

        self.start_gene = Gene.objects.create(
            hgnc_id="HGNC:0001"
        )

        self.start_transcript = Transcript.objects.get_or_create(
            transcript="NM00045.6",
            gene=self.start_gene,
            reference_genome="37"
        )
    

    def test_add_old_gene_changed_transcript(self):
        """
        We expect there to be 2 copies of NM00045.6, one for each
        reference genome
        """
        err = []

        hgnc_id = "HGNC:0001"
        transcripts = "NM00045.6"
        reference = "38"
        source = "HGMD"

        hgmd_release_label = "release_2"
        tx_mane_release = "1.0"
        mane_ext_id = "file-123"
        mane_ftp_ext_id = "file-234"
        g2refseq_ext_id = "file-345"
        markname_ext_id = "file-456"
        
        _add_clinical_gene_and_transcript_to_db(hgnc_id, transcripts, reference, source,
                                                hgmd_release_label, tx_mane_release, mane_ext_id,
                                                mane_ftp_ext_id, g2refseq_ext_id, markname_ext_id)

        all_transcripts = Transcript.objects.all()

        # expect old and new copy for the same transcript
        err += len_check_wrapper(all_transcripts, "transcript", 2)
        new_tx = all_transcripts[1]
        err += value_check_wrapper(new_tx.transcript, "transcript name", "NM00045.6")
        err += value_check_wrapper(new_tx.reference_genome, "ref", "38")

        errors = "; ".join(err)
        assert not errors, errors
