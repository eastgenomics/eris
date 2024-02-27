from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist

from panels_backend.management.commands.generate import Command
from panels_backend.models import (
    ReferenceGenome,
    GffRelease
)


class TestCheckCatchesNoRefGenome(TestCase):
    def test_no_reference(self):
        """
        CASE: No reference genome or GFF are in the database
        EXPECT: Error thrown over the lack of reference genome
        """
        cmd = Command()
        ref = "GRCh37"
        gff = "19"
        expected_err = "Aborting g2t: reference genome does not exist in "
        "the database"
        with self.assertRaisesRegex(ObjectDoesNotExist, expected_err):
            cmd._check_genome_and_gff_in_db(ref, gff)


class TestCheckCatchesNoGff(TestCase):
    def setUp(self) -> None:
        ReferenceGenome.objects.create(
            name="GRCh37"
        )
    
    def test_no_gff(self):
        """
        CASE: A GFF is missing in the database
        EXPECT: Error thrown over the lack of GFF
        """
        cmd = Command()
        ref = "GRCh37"
        gff = "19"
        expected_err = "Aborting g2t: GFF release does not exist for this "
        "genome build in the database"
        with self.assertRaisesRegex(ObjectDoesNotExist, expected_err):
            cmd._check_genome_and_gff_in_db(ref, gff)


class TestGenomeGffPass(TestCase):
    def setUp(self) -> None:
        self.ref = ReferenceGenome.objects.create(
            name="GRCh37"
        )

        self.gff = GffRelease.objects.create(
            ensembl_release="19",
            reference_genome=self.ref
        )
    
    def test_no_gff(self):
        """
        CASE: Both reference and GFF are present in DB
        EXPECT: The reference and GFF are correctly returned
        """
        cmd = Command()
        ref = "GRCh37"
        gff = "19"

        genome, gff = cmd._check_genome_and_gff_in_db(ref, gff)
        assert genome == self.ref
        assert gff == self.gff
