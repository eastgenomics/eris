from django.test import TestCase


from panels_backend.management.commands._parse_transcript import _parse_reference_genome


class TestParsingRefGenome(TestCase):
    """
    Test various valid ref genome values return the 'standardised' string.
    For example, 'hg19' should be turned into 'GRCh37'.
    Additionally, test invalid ref genome values raise a ValueError and error message.
    """

    def test_ref_genome_values_37(self):
        """
        Check valid synonyms for GRCh37 are converted
        """
        valid = ["37", "GRCh37", "Grch37", "hg19", "HG19", "hG19"]
        for i in valid:
            with self.subTest():
                self.assertEqual(_parse_reference_genome(i), "GRCh37")

    def test_ref_genome_values_37_with_patch(self):
        """
        Check valid synonyms for GRCh37 are converted
        """
        valid = ["GRCh37.p10", "Grch37.P10", "hg19.P10"]
        for i in valid:
            with self.subTest():
                self.assertEqual(_parse_reference_genome(i), "GRCh37.p10")

    def test_ref_genome_values_38(self):
        """
        Check valid synonyms for GRCh38 are converted
        """
        valid = ["38", "GRCh38", "Grch38", "hg38", "HG38", "hG38"]
        for i in valid:
            with self.subTest():
                self.assertEqual(_parse_reference_genome(i), "GRCh38")

    def test_ref_genome_values_38_with_patch(self):
        """
        Check valid synonyms for GRCh37 are converted
        """
        valid = ["GRCh38.p10", "Grch38.p10", "hg38.P10"]
        for i in valid:
            with self.subTest():
                self.assertEqual(_parse_reference_genome(i), "GRCh38.p10")

    def test_invalid_ref_genomes(self):
        """
        Check that nonsense strings throw a ValueError and a handy message
        """
        invalid = [
            "1234",
            "beans",
            "£&£*$",
            "GRCh37.p12not_a_real_patch",
            "GRCh38.p12not_a_real_patch",
        ]

        permitted_grch37 = ["hg19", "37", "grch37"]
        permitted_grch38 = ["hg38", "38", "grch38"]

        for i in invalid:
            with self.subTest():
                msg = f"Please provide a valid reference genome, such as {'; '.join(permitted_grch37)}, "
                f"{'; '.join(permitted_grch38)} or GRCh37/GRCh38 followed by '.p' patch numbers - you provided {i}"
                with self.assertRaises(ValueError) as cm:
                    _parse_reference_genome(i)
                    self.assertEqual(msg, cm.exception)
