from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist

from panels_backend.management.commands.generate import Command
from panels_backend.models import (
    ReferenceGenome,
)


class TestCheckCatchesNoRefGenome(TestCase):
    def test_no_reference(self):
        """
        CASE: No reference genome is in the database
        EXPECT: Error thrown over the lack of reference genome
        """
        cmd = Command()
        ref = "GRCh37"
        expected_err = "Aborting g2t: reference genome does not exist in "
        "the database"
        with self.assertRaisesRegex(ObjectDoesNotExist, expected_err):
            cmd._check_genome_in_db(ref)


class TestRefGenomePass(TestCase):
    def setUp(self) -> None:
        self.ref = ReferenceGenome.objects.create(
            name="GRCh37"
        )
    
    def test_no_gff(self):
        """
        CASE: ReferenceGenome is present in DB
        EXPECT: The reference is correctly returned
        """
        cmd = Command()
        ref = "GRCh37"
        gff = "19"

        genome = cmd._check_genome_in_db(ref)
        assert genome == self.ref
