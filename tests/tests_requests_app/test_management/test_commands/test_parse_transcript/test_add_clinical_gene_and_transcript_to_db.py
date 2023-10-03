from django.test import TestCase


from requests_app.models import \
    Gene, Transcript, TranscriptSource, TranscriptRelease,\
    TranscriptReleaseLink


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
        Straightforward use case: there is one transcript per gene.
        We expect the transcript, gene, release, source of data, and link between tx
        and gene to be added to the db.
        """
        err = []

        hgnc_id = "HGNC:0001"
        transcript = "NM00045.6"
        reference = "37"
        source = "MANE"
        release_version = "release_2"
        match_full_version = True
        file_info = {"file-123": "mane_grch37",
                     "file-234": "mane_hrch38_ftp"}

        _add_clinical_gene_and_transcript_to_db(hgnc_id, transcript, reference, source,
                                                release_version, match_full_version,
                                                file_info)

        new_genes = Gene.objects.all()
        new_sources = TranscriptSource.objects.all()
        new_transcripts = Transcript.objects.all()
        new_links = TranscriptReleaseLink.objects.all()
        new_release = TranscriptRelease.objects.all()

        # Check that the expected genes were added to the database
        err += len_check_wrapper(new_genes, "gene", 1)
        err += value_check_wrapper(new_genes[0].hgnc_id, "gene HGNC", "HGNC:0001")
        err += value_check_wrapper(new_genes[0].gene_symbol, "gene symbol", None)

        # Check that the sources were added
        err += len_check_wrapper(new_sources, "tx source", 1)
        err += value_check_wrapper(new_sources[0].source, "tx source", "MANE")

        # Check that the transcripts were added
        err += len_check_wrapper(new_transcripts, "transcript", 1)
        err += value_check_wrapper(new_transcripts[0].transcript, "transcript name",
                                   "NM00045.6")
        err += value_check_wrapper(new_transcripts[0].reference_genome, "ref", "37")

        # Check that there's a release
        err += len_check_wrapper(new_release, "release", 1)
        err += value_check_wrapper(new_release[0].external_release_version, "release",
                                   "release_2")

        # Check that the transcript is linked to the release
        err += len_check_wrapper(new_links, "links", 1)
        err += value_check_wrapper(new_links[0].match_version, "link match version", True)
        err += value_check_wrapper(new_links[0].release, "link release", new_release[0])
        err += value_check_wrapper(new_links[0].transcript, "link tx", new_transcripts[0])

        errors = "; ".join(err)
        assert not errors, errors


class TestAddGeneTranscript_AlreadyExists(TestCase):
    """
    Cases where transcripts are being added to a database which
    already contains a gene and transcript.

    The second transcript will be added - this can happen if e.g. the
    reference genome for one is 37, and for the other, it is 38.
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
        Scenario: a new transcript is added to a database. Its gene is
        already in the database, as is a different transcript for that gene.

        Expect: 2 copies of NM00045.6 in Transcript, one for each reference genome
        We also expect release and linking table to be in the database.
        """
        err = []

        hgnc_id = "HGNC:0001"
        transcript = "NM00045.6"
        reference = "38"
        source = "HGMD"

        release_version = "release_2"
        match_full_version = False
        file_info = {"file-345": "hgmd_gene2refseq",
                     "file-456": "hgmd_markname"}

        _add_clinical_gene_and_transcript_to_db(hgnc_id, transcript, reference, source,
                                                release_version, match_full_version,
                                                file_info)

        all_transcripts = Transcript.objects.all()
        new_links = TranscriptReleaseLink.objects.all()
        new_release = TranscriptRelease.objects.all()

        # expect old and new copy for the same transcript
        err += len_check_wrapper(all_transcripts, "transcript", 2)
        
        old_tx = all_transcripts[0]
        err += value_check_wrapper(old_tx.transcript, "transcript name", "NM00045.6")
        err += value_check_wrapper(old_tx.reference_genome, "ref", "37")
        
        new_tx = all_transcripts[1]
        err += value_check_wrapper(new_tx.transcript, "transcript name", "NM00045.6")
        err += value_check_wrapper(new_tx.reference_genome, "ref", "38")

        # Check that there's a release in the database
        err += len_check_wrapper(new_release, "release", 1)
        err += value_check_wrapper(new_release[0].external_release_version, "release",
                                   "release_2")

        # Check that there's only one link between transcript (our new one, as we didn't
        # make a link at set-up) and the release version
        err += len_check_wrapper(new_links, "links", 1)
        err += value_check_wrapper(new_links[0].match_version, "link match version", False)
        err += value_check_wrapper(new_links[0].release, "link release", new_release[0])
        err += value_check_wrapper(new_links[0].transcript, "link tx", new_tx)

        errors = "; ".join(err)
        assert not errors, errors
