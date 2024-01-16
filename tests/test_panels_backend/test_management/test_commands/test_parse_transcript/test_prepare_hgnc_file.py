from django.test import TestCase
from panels_backend.models import Gene
from panels_backend.management.commands._parse_transcript import prepare_hgnc_file


class TestPrepareHgncFile(TestCase):
    """
    Test the function prepare_hgnc_file in _parse_transcript.py
    """

    def setUp(self) -> None:
        (
            self.gene_symbols_to_hgnc_ids,
            self.hgnc_id_to_approved_symbol,
            self.hgnc_id_to_alias_symbols,
        ) = prepare_hgnc_file("testing_files/eris/hgnc_dump_mock.txt")

    def test_prepare_hgnc_file_in_general(self):
        """
        CASE: Test that the function returns dict using the mock testing file
        EXPECT: 15 entries as per the mock file
        """
        assert len(self.gene_symbols_to_hgnc_ids) == 15
        assert len(self.hgnc_id_to_approved_symbol) == 15
        assert len(self.hgnc_id_to_alias_symbols) == 7

        assert self.hgnc_id_to_alias_symbols["HGNC:18149"] == [
            "A14GALT",
            " Gb3S",
            " P(k)",
        ]
