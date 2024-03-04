from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist

from panels_backend.management.commands.generate import Command
from panels_backend.models import ReferenceGenome, GffRelease


class TestCheckCatchesNoGff(TestCase):
    def setUp(self) -> None:
        self.ref = ReferenceGenome.objects.create(name="GRCh37")

    def test_no_gff(self):
        """
        CASE: A GFF is missing in the database
        EXPECT: Error thrown over the lack of GFF
        """
        cmd = Command()
        gff = "19"
        expected_err = "Aborting g2t: GFF release does not exist for this "
        "genome build in the database"
        with self.assertRaisesRegex(ObjectDoesNotExist, expected_err):
            cmd._check_gff_in_db(gff, self.ref)


class TestGffPass(TestCase):
    def setUp(self) -> None:
        self.ref = ReferenceGenome.objects.create(name="GRCh37")

        self.gff = GffRelease.objects.create(
            ensembl_release="19", reference_genome=self.ref
        )

    def test_no_gff(self):
        """
        CASE: The GFF is present in the DB
        EXPECT: The GFF is correctly returned
        """
        cmd = Command()
        gff = "19"

        gff = cmd._check_gff_in_db(gff, self.ref)
        assert gff == self.gff
