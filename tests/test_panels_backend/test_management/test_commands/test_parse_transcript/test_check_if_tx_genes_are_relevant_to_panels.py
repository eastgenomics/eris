from django.test import TestCase
from unittest import mock

from panels_backend.management.commands._parse_transcript import (
    _check_if_tx_genes_are_relevant_to_panels,
)
from panels_backend.models import (
    ReferenceGenome,
    Gene,
    Transcript,
    Panel,
    PanelGene,
)


class TestCheckMoreThanOneTxMatch_MultiMatches(TestCase):
    """
    Cases where there are multiple matches
    """

    def setUp(self) -> None:
        """
        For both the cases, we need a transcript, and multiple genes to
        which it is linked.
        """
        # set up reference genome and genes
        self.ref_genome = ReferenceGenome.objects.create(name="GRCh37")

        self.gene_1 = Gene.objects.create(hgnc_id="HGNC:1", gene_symbol="YFG1")

        self.gene_2 = Gene.objects.create(hgnc_id="HGNC:2", gene_symbol="YFG2")

        # note these Tx database entries have the same transcript name,
        # but different genes
        self.tx = Transcript.objects.create(
            transcript="NM00234.1",
            gene=self.gene_1,
            reference_genome=self.ref_genome,
        )

        self.tx = Transcript.objects.create(
            transcript="NM00234.1",
            gene=self.gene_2,
            reference_genome=self.ref_genome,
        )

    def test_returns_true_and_err_message(self):
        """
        CASE: there are multiple genes linked to a tx, but none of the
        genes are relevant to our current panels.
        EXPECT: return True for multi-match, and an error message, but
        don't stop the script.
        """
        matches = [
            {
                "HGNC ID": "HGNC:1",
                "MANE TYPE": "MANE SELECT",
                "RefSeq": "NM00234.1",
                "RefSeq_versionless": "NM00234",
            },
            {
                "HGNC ID": "HGNC:2",
                "MANE TYPE": "MANE PLUS CLINICAL",
                "RefSeq": "NM00234.1",
                "RefSeq_versionless": "NM00234",
            },
        ]
        tx = "NM00234.1"

        err = _check_if_tx_genes_are_relevant_to_panels(matches, tx)

        assert (
            err
            == f"Versionless transcript in MANE more than once, can't resolve: {tx}"
        )

    def test_throws_value_error(self):
        """
        CASE: there are multiple genes linked to a tx, and a gene IS IN a
         current panel.
        EXPECT: throw a script-stopping exception.
        """
        # add a PanelGene entry to make the gene relevant
        self.panel = Panel.objects.create(
            external_id="3",
            panel_name="My panel",
            panel_source="PanelApp",
            panel_version="00001.00000",
        )

        PanelGene.objects.create(
            panel=self.panel,
            gene=self.gene_1,
            justification="PanelApp",
            active=True,
        )

        matches = [
            {
                "HGNC ID": "HGNC:1",
                "MANE TYPE": "MANE SELECT",
                "RefSeq": "NM00234.1",
                "RefSeq_versionless": "NM00234",
            },
            {
                "HGNC ID": "HGNC:2",
                "MANE TYPE": "MANE PLUS CLINICAL",
                "RefSeq": "NM00234.1",
                "RefSeq_versionless": "NM00234",
            },
        ]
        tx = "NM00234.1"

        expected_err = (
            f"Versionless transcript in MANE more than once and linked"
            f" to multiple panel-relevant genes, can't resolve: {tx}"
        )

        with self.assertRaisesRegex(ValueError, expected_err):
            err = _check_if_tx_genes_are_relevant_to_panels(matches, tx)
