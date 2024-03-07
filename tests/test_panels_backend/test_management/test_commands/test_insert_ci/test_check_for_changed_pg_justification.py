from django.test import TestCase

from panels_backend.models import Panel, Gene, PanelGene, PanelGeneHistory
from panels_backend.management.commands.history import History
from panels_backend.management.commands._insert_ci import (
    _check_for_changed_pg_justification,
)


class TestCheckChangedPg_Unchanged(TestCase):
    def setUp(self) -> None:
        self.panel = Panel.objects.create(
            external_id=None,
            panel_name="My panel",
            panel_version=None,
            panel_source="National-genomic-test-directory-for-rare-and-"
            "inherited-disease-version-5.xlsx + 230401_RD + 230616",
            test_directory=True,
        )

        self.gene = Gene.objects.create(
            hgnc_id="HGNC:1049", gene_symbol="YFG1", alias_symbols=None
        )

        self.pg = PanelGene.objects.create(
            panel=self.panel,
            gene=self.gene,
            justification="National-genomic-test-directory-for-rare-and-"
            "inherited-disease-version-5.xlsx + 230401_RD + 230616",
            active=True,
        )

        self.user = None  # mimicking running from CLI

    def test_pg_justification_is_changed(self):
        """
        CASE: A db is seeded with a new test directory JSON.
        A PanelGene which is in the new JSON already exists in the db from
        an older test directory JSON
        EXPECT: No change is made and no history is logged.
        """
        td_source = "National-genomic-test-directory-for-rare-and-inherited-disease-version-5.xlsx + 230401_RD + 230616"

        _check_for_changed_pg_justification(self.pg, td_source, self.user)

        # check there's no new PanelGene and no change to the original entry
        with self.subTest():
            assert len(PanelGene.objects.all()) == 1
            assert PanelGene.objects.all()[0].justification == td_source

        # check there's no history entry
        with self.subTest():
            pg_history = PanelGeneHistory.objects.all()
            assert len(pg_history) == 0


class TestCheckChangedPg_IsChanged(TestCase):
    def setUp(self) -> None:
        self.panel = Panel.objects.create(
            external_id=None,
            panel_name="My panel",
            panel_version=None,
            panel_source="National-genomic-test-directory-for-rare-and-"
            "inherited-disease-version-5.xlsx + 230401_RD + 230616",
            test_directory=True,
        )

        self.gene = Gene.objects.create(
            hgnc_id="HGNC:1049", gene_symbol="YFG1", alias_symbols=None
        )

        self.pg = PanelGene.objects.create(
            panel=self.panel,
            gene=self.gene,
            justification="National-genomic-test-directory-for-rare-and-"
            "inherited-disease-version-5.xlsx + 230401_RD + 230616",
            active=True,
        )

        self.user = None  # mimicking running from CLI

    def test_pg_justification_is_changed(self):
        """
        CASE: A db is seeded with a new version of a test directory.
        A PanelGene which already exists in the db, persists in the new
         TD JSON.
        EXPECT: The justification is updated to the new TD JSON,
          and the history is logged.
        """
        old_td_source = "National-genomic-test-directory-for-rare-and-inherited-disease-version-5.xlsx + 230401_RD + 230616"
        new_td_source = "National-genomic-test-directory-for-rare-and-inherited-disease-version-6.xlsx + test + test"

        _check_for_changed_pg_justification(self.pg, new_td_source, self.user)

        # check the PanelGene has updated
        with self.subTest():
            assert len(PanelGene.objects.all()) == 1
            assert PanelGene.objects.all()[0].justification == new_td_source

        # check there's a history entry and that it's formatted correctly
        with self.subTest():
            pg_history = PanelGeneHistory.objects.all()
            assert len(pg_history) == 1

            expected_note = History.panel_gene_metadata_changed(
                "justification",
                old_td_source,
                new_td_source,
            )
            assert pg_history[0].note == expected_note
