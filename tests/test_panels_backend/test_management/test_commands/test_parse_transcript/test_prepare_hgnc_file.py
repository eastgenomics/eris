from django.test import TestCase
from panels_backend.models import Gene, HgncRelease
from panels_backend.management.commands._parse_transcript import _prepare_hgnc_file


class TestPrepareHgncFile(TestCase):
    """
    Test the function prepare_hgnc_file in _parse_transcript.py
    """

    def setUp(self) -> None:
        self.gene_symbols_to_hgnc_ids = _prepare_hgnc_file(
            "testing_files/eris/hgnc_dump_mock.txt", "1.0", "mock_user"
        )

    def test_prepare_hgnc_file_in_general(self):
        """
        CASE: Test that the function returns dict using the mock testing file
        EXPECT: 15 entries as per the mock file
        """
        assert len(self.gene_symbols_to_hgnc_ids) == 15

    def test_new_gene_bulk_create(self):
        """
        CASE: Test that the function creates new genes in the database
        EXPECT: 15 new entries in the database as per the mock file
        """
        assert Gene.objects.count() == 15

    def test_hgnc_release_created(self):
        """
        CASE: Test that the function create a new hgnc release in the database
        EXPECT: 1 new entry in the database
        """
        assert HgncRelease.objects.count() == 1

    def test_alias_created(self):
        """
        CASE: Test that the function create a new alias in the database
        EXPECT: 1 new entry in the database
        """
        gene = Gene.objects.get(hgnc_id="HGNC:30005")
        assert gene.alias_symbols == "IGB3S,IGBS3S"


class TestChangeScenario(TestCase):
    """
    Test the function prepare_hgnc_file in _parse_transcript.py
    in particularly in scenario where gene symbol changes or alias symbols changes
    """

    def setUp(self) -> None:
        self.gene = Gene.objects.create(
            hgnc_id="HGNC:5",
            gene_symbol="ABC",
        )  # this is the wrong symbol for HGNC:5

        self.second_gene = Gene.objects.create(
            hgnc_id="HGNC:30005",
            alias_symbols="A,B,C",  # this alias symbols are wrong for HGNC:30005
        )

        _prepare_hgnc_file("testing_files/eris/hgnc_dump_mock.txt", "1.0", "mock_user")

    def test_when_gene_symbol_changes(self):
        """
        CASE: new HGNC file have a different gene symbol for the same HGNC ID
        EXPECT: the gene symbol in the database should be updated
        """

        self.gene.refresh_from_db()
        assert self.gene.gene_symbol == "A1BG"

    def test_when_alias_symbols_changed(self):
        """
        CASE: new HGNC file have a different alias symbols for the same HGNC ID
        EXPECT: the alias symbols in the database should be updated by the function
        """
        self.second_gene.refresh_from_db()
        assert self.second_gene.alias_symbols == "IGB3S,IGBS3S"
