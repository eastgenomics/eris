"""
A few scenarios tested here for insert_gene function

- linking a new gene to a new panel
- skipping a gene with low confidence and only taking the gene with confidence level 3
- skipping a gene with no hgnc-id
- not change anything to existing panel-gene link if it is unchanged in PanelApp API
- flagging panel-gene interaction with confidence less than 3 in subsequent PanelApp API seed
- flagging new panel-gene link on existing panel with linked genes
"""


from django.test import TestCase

from requests_app.models import (
    Panel,
    Gene,
    PanelGene,
    PanelGeneHistory,
    Confidence,
    ModeOfInheritance,
    Penetrance,
    ModeOfPathogenicity,
)

from requests_app.management.commands._insert_panel import _insert_gene

from requests_app.management.commands.history import History
from requests_app.management.commands.panelapp import PanelClass


def len_check_wrapper(metric, metric_name, expected) -> str | list:
    """
    Checks that length of a list of metrics matches the expected length.
    Returns an error if not, otherwise returns an empty list.
    Saves a line of code every time I have to check that a data table
    contains the expected number of entries.
    """
    if len(metric) != expected:
        msg = (
            f"The number of {metric_name} entries in the database is {len(metric)} "
            f"which does not match the expected: {expected}"
        )
        return msg
    else:
        return []  # empty list


def value_check_wrapper(metric, metric_name, expected) -> str | list:
    """
    Checks that value of a metric matches the expected value.
    Returns an error if not, otherwise returns an empty list.
    Saves formatting the error message constantly.
    """
    if metric != expected:
        msg = f"The value of {metric_name} is {metric} which does not match the expected: {expected}"
        return msg
    else:
        return []


class TestInsertGene_NewGene(TestCase):
    """
    Situation where panel created and gene created
    """

    errors = []  # list of errors to be reported at the end

    def setUp(self) -> None:
        """
        Start condition: Make a Panel, which we will link to genes as part of testing
        _insert_gene
        """
        self.first_panel = Panel.objects.create(
            external_id="1141",
            panel_name="Acute rhabdomyolosis",
            panel_source="PanelApp",
            panel_version="1.15",
        )

    def test_new_panel_linked_to_acceptable_gene(self):
        """
        Test that `insert_gene` function will create
        panel-gene link for a new panel and a new gene
        """

        test_panel = PanelClass(
            id="1141",
            name="Acute rhabdomyolyosis",
            version="1.15",
            panel_source="PanelApp",
            genes=[
                {
                    "gene_data": {
                        "hgnc_id": 21497,
                        "gene_name": "acyl-CoA dehydrogenase family member 9",
                        "gene_symbol": "ACAD9",
                        "alias": ["NPD002", "MGC14452"],
                    },
                    "confidence_level": 3,
                }
            ],
            regions=[],
        )

        # run the function under test
        _insert_gene(test_panel, self.first_panel, True)

        # there should only be one gene added into test db
        new_genes = Gene.objects.all()
        if not len(new_genes) == 1:
            self.errors.append("There should only be one gene in the database")

        # assert the inserted gene should have above gene metadata
        new_gene = new_genes[0]
        if (
            not new_gene.hgnc_id == "21497"
            or not new_gene.gene_symbol == "ACAD9"
            or not new_gene.alias_symbols == "NPD002,MGC14452"
        ):
            self.errors.append(
                "The gene added to the database does not have the correct metadata"
            )

        # assert that there is only one panel-gene inserted into test db
        panel_genes = PanelGene.objects.filter(
            panel=self.first_panel.id, gene=new_gene.id
        )
        if not len(panel_genes) == 1:
            self.errors.append("There should only be one panel-gene in the database")

        new_panelgene = panel_genes[0]
        confidence = Confidence.objects.get(id=new_panelgene.confidence.id)

        # assert that the panel-gene have conf level 3
        if not confidence.confidence_level == "3":
            self.errors.append(
                "The panel-gene added to the database does not have the correct confidence level"
            )

        # check a history record was made for a NEW link
        panel_gene_history = PanelGeneHistory.objects.filter(
            panel_gene=new_panelgene.id
        )
        if not len(panel_gene_history) == 1:
            self.errors.append("There should only be one history record")

        # check panel-gene history record user as PanelApp
        new_history = panel_gene_history[0]

        if not new_history.user == "PanelApp":
            self.errors.append(
                "The panel-gene history record does not have the correct user"
            )

        assert not self.errors, self.errors

    def test_reject_low_confidence_gene(self):
        """
        Test that when panel have genes of lower confidence (0, 1, 2),
        `insert_gene` function will not insert them into database
        """

        # make one of the test inputs for the function
        test_panel = PanelClass(
            id="1141",
            name="Acute rhabdomyolyosis",
            version="1.15",
            panel_source="PanelApp",
            genes=[
                {
                    "gene_data": {
                        "hgnc_id": 21497,
                        "gene_name": "acyl-CoA dehydrogenase family member 9",
                        "gene_symbol": "ACAD9",
                        "alias": ["NPD002", "MGC14452"],
                    },
                    "confidence_level": 2,
                },
                {
                    "gene_data": {
                        "hgnc_id": 89,
                        "gene_name": "medium-chain acyl-CoA dehydrogenase",
                        "gene_symbol": "ACADM",
                        "alias": ["MCAD", "MCADH", "ACAD1"],
                    },
                    "confidence_level": 3,
                },
            ],
            regions=[],
        )

        # run the function under test
        _insert_gene(test_panel, self.first_panel, False)

        # check there is a panel entry - this was in the DB already
        new_panels = Panel.objects.all()
        if not len(new_panels) == 1:
            self.errors.append("There should only be one panel in the database")

        # there will only be one gene in db because we ignore the gene with confidence level 2
        new_genes = Gene.objects.all()
        if not len(new_genes) == 1:
            self.errors.append("There should only be one gene in the database")

        # check 1 panel-gene entry, which will be for the gene with HGNC 89
        new_panel_genes = PanelGene.objects.all()
        if not len(new_panel_genes) == 1:
            self.errors.append("There should only be one panel-gene in the database")

        # check 1 history entry
        new_history = PanelGeneHistory.objects.all()
        if not len(new_history) == 1:
            self.errors.append("There should only be one history record")

        assert not self.errors, self.errors

    def test_rejects_no_hgnc_id_gene(self):
        """
        Test that `insert_gene` function will not create
        panel-gene link for gene with no hgnc-id
        """

        # make one of the test inputs for the function
        test_panel = PanelClass(
            id="1141",
            name="Acute rhabdomyolyosis",
            version="1.15",
            panel_source="PanelApp",
            genes=[
                {
                    "gene_data": {
                        "hgnc_id": None,  # notice the None
                        "gene_name": "acyl-CoA dehydrogenase family member 9",
                        "gene_symbol": "ACAD9",
                        "alias": ["NPD002", "MGC14452"],
                    },
                    "confidence_level": 3,
                },
                {
                    "gene_data": {
                        "hgnc_id": 89,
                        "gene_name": "medium-chain acyl-CoA dehydrogenase",
                        "gene_symbol": "ACADM",
                        "alias": ["MCAD", "MCADH", "ACAD1"],
                    },
                    "confidence_level": 3,
                },
            ],
            regions=[],
        )

        # run the function under test
        _insert_gene(test_panel, self.first_panel, True)

        # check there is a panel entry - this was in the DB already
        new_panels = Panel.objects.all()
        if not len(new_panels) == 1:
            self.errors.append("There should only be one panel in the database")

        # check that the no-HGNC ID gene was NOT added to the database
        # only the gene with hgnc_id 89 should be in there
        new_genes = Gene.objects.all()
        if not len(new_genes) == 1:
            self.errors.append("There should only be one gene in the database")

        # check 1 panel-gene entry, which will be for the gene with HGNC 89
        new_panel_genes = PanelGene.objects.all()
        if not len(new_panel_genes) == 1:
            self.errors.append("There should only be one panel-gene in the database")

        # check 1 history entry
        new_history = PanelGeneHistory.objects.all()
        if not len(new_history) == 1:
            self.errors.append(
                "There should only be one history record"
            )  # assert that history is created for one panel-gene link created


class TestInsertGene_PreexistingGene_PreexistingPanelappPanelLink(TestCase):
    """
    situation where a panel has already been previously added to the db
    with linked up panel-gene and the new panel and panel-gene seeded
    from PanelApp API call is the same as the one in the database
    so we expect no change to happen
    """

    errors = []

    def setUp(self) -> None:
        """
        Start condition: Make a Panel, and linked genes
        """
        self.first_panel = Panel.objects.create(
            external_id="1141",
            panel_name="Acute rhabdomyolosis",
            panel_source="PanelApp",
            panel_version="1.15",
        )

        self.first_gene = Gene.objects.create(
            hgnc_id="21497",
            gene_symbol="ACAD9",
            alias_symbols="NPD002,MGC14452",
        )

        self.confidence = Confidence.objects.create(confidence_level=3)

        self.moi = ModeOfInheritance.objects.create(mode_of_inheritance="test")

        self.mop = ModeOfPathogenicity.objects.create(mode_of_pathogenicity="test")

        self.penetrance = Penetrance.objects.create(penetrance="test")

        self.first_link = PanelGene.objects.create(
            panel=self.first_panel,
            gene=self.first_gene,
            confidence_id=self.confidence.id,
            moi_id=self.moi.id,
            mop_id=self.mop.id,
            penetrance_id=self.penetrance.id,
            justification="PanelApp",
        )

    def test_that_unchanged_gene_is_ignored(self):
        """
        Test that for a panel-gene combination that is already in the database,
        and not updated in the PanelApp API call, we don't change them
        """

        # make one of the test inputs for the function
        test_panel = PanelClass(
            id="1141",
            name="Acute rhabdomyolyosis",
            version="1.15",
            panel_source="PanelApp",
            genes=[
                {
                    "gene_data": {
                        "hgnc_id": 21497,
                        "gene_name": "acyl-CoA dehydrogenase family member 9",
                        "gene_symbol": "ACAD9",
                        "alias": ["NPD002", "MGC14452"],
                    },
                    "confidence_level": 3,
                    "mode_of_inheritance": "test",
                    "mode_of_pathogenicity": "test",
                    "penetrance": "test",
                }
            ],
            regions=[],
        )

        # run the function under test
        _insert_gene(
            test_panel, self.first_panel, False
        )  # False for `panel_created` because the panel already exist in the database with unchanged `external_id` `panel_name` and `panel_version`

        # check that the gene is in the database
        # and that it is unchanged from when we first added it
        new_genes = Gene.objects.all()
        if not len(new_genes) == 1:
            self.errors.append("There should only be one gene in the database")

        new_gene = new_genes[0]
        if not new_gene.hgnc_id == "21497":
            self.errors.append(
                "The gene added to the database does not have the correct metadata"
            )

        # check that we still have just 1 PanelGene link, which should be the one
        # we made ourselves in set-up
        panel_genes = PanelGene.objects.all()
        if not len(panel_genes) == 1:
            self.errors.append("There should only be one panel-gene in the database")

        if panel_genes[0].pending:
            self.errors.append(
                "The panel-gene should not be flagged"
            )  # check that the panel-gene interaction is not flagged up

        # the gene will be in the database, but it will be the old record
        new_panelgene = panel_genes[0]
        confidence = Confidence.objects.get(id=new_panelgene.confidence.id)
        if not confidence.confidence_level == "3":
            self.errors.append(
                "The panel-gene added to the database does not have the correct confidence level"
            )

        # there should not have been a history record made,
        # because there was not a change to the gene-panel link in this upload
        panel_gene_history = PanelGeneHistory.objects.all()
        if not len(panel_gene_history) == 0:
            self.errors.append("There should be no history record")

        assert not self.errors, self.errors


class TestAdditionOfGeneToExistingPanelGene(TestCase):
    """
    Test that `insert_gene` function will create new panel-gene
    for existing panel with existing genes but flag it up for manual review
    """

    errors = []

    def setUp(self) -> None:
        self.first_panel = Panel.objects.create(
            external_id="1141",
            panel_name="Acute rhabdomyolosis",
            panel_source="PanelApp",
            panel_version="1.15",
        )

        self.first_gene = Gene.objects.create(
            hgnc_id="21497",
            gene_symbol="ACAD9",
            alias_symbols="NPD002,MGC14452",
        )

        self.confidence = Confidence.objects.create(confidence_level=3)

        self.moi = ModeOfInheritance.objects.create(mode_of_inheritance="test")

        self.mop = ModeOfPathogenicity.objects.create(mode_of_pathogenicity="test")

        self.penetrance = Penetrance.objects.create(penetrance="test")

        self.first_link = PanelGene.objects.create(
            panel=self.first_panel,
            gene=self.first_gene,
            confidence_id=self.confidence.id,
            moi_id=self.moi.id,
            mop_id=self.mop.id,
            penetrance_id=self.penetrance.id,
            justification="PanelApp",
        )

    def test_that_new_gene_addition_will_be_flagged(self):
        """
        example scenario:
        Panel A is linked to Gene A
        In the new PanelApp API, Panel A is linked to Gene A and Gene B
        We expect that Gene B will be added to the database, but the panel-gene link
        between Panel A and Gene B be flagged for manual review
        """
        # make one of the test inputs for the function
        test_panel = PanelClass(
            id="1141",
            name="Acute rhabdomyolyosis",
            version="1.16",  # note version change
            panel_source="PanelApp",
            genes=[
                {
                    "gene_data": {
                        "hgnc_id": 21497,
                        "gene_name": "acyl-CoA dehydrogenase family member 9",
                        "gene_symbol": "ACAD9",
                        "alias": ["NPD002", "MGC14452"],
                    },
                    "confidence_level": 3,
                    "mode_of_inheritance": "test",
                    "mode_of_pathogenicity": "test",
                    "penetrance": "test",
                },
                {
                    "gene_data": {
                        "hgnc_id": 89,
                        "gene_name": "medium-chain acyl-CoA dehydrogenase",
                        "gene_symbol": "ACADM",
                        "alias": ["MCAD", "MCADH", "ACAD1"],
                    },
                    "confidence_level": 3,
                },
            ],
            regions=[],
        )

        # run the function under test
        _insert_gene(
            test_panel, self.first_panel, False
        )  # False because it's an existing panel

        all_genes = Gene.objects.all()
        if not len(all_genes) == 2:
            self.errors.append("There should be two genes in the database")

        second_gene = all_genes[1]
        if not second_gene.hgnc_id == "89":
            self.errors.append("The gene added to the database should have hgnc_id 89")

        panel_genes = PanelGene.objects.all()
        if not len(panel_genes) == 2:
            self.errors.append("There should be two panel-gene links in the database")

        # check that the first panel-gene link is unchanged
        if not panel_genes[0].id == self.first_link.id:
            self.errors.append(
                "The first panel-gene link should be unchanged"
            )  # assert that the first panel is the same as the one we made in set-up

        second_panel_gene = panel_genes[1]
        if not second_panel_gene.pending:
            self.errors.append("The second panel-gene link should be flagged")

        if not second_panel_gene.gene_id == second_gene.id:
            self.errors.append(
                "The second panel-gene link should be linked to the second gene"
            )

        # History record should link the old gene to the new panel version
        panel_gene_history = PanelGeneHistory.objects.all()
        if not len(panel_gene_history) == 1:
            self.errors.append(
                "There should be one history record"
            )  # there should only be one history recorded as we didn't create history for the panel-gene we created in setup. This history is created by `insert_gene` when creating the second panel-gene

        if not panel_gene_history[0].panel_gene == panel_genes[1]:
            self.errors.append(
                "The history record should link to the second panel-gene"
            )

        assert not self.errors, self.errors


class TestDropInPanelGeneConfidence(TestCase):
    """
    Test for `insert_gene` to flag panel-gene link when there is
    drop in panel-gene confidence in new PanelApp API seed
    """

    errors = []

    def setUp(self) -> None:
        self.first_panel = Panel.objects.create(
            external_id="1141",
            panel_name="Acute rhabdomyolosis",
            panel_source="PanelApp",
            panel_version="1.15",
        )

        self.first_gene = Gene.objects.create(
            hgnc_id="21497",
            gene_symbol="ACAD9",
            alias_symbols="NPD002,MGC14452",
        )

        self.second_gene = Gene.objects.create(
            hgnc_id="89",
            gene_symbol="ACADM",
            alias_symbols="MCAD,MCADH,ACAD1",
        )

        # all metadata for panel-gene link
        self.confidence = Confidence.objects.create(confidence_level=3)

        self.moi = ModeOfInheritance.objects.create(mode_of_inheritance="test")

        self.mop = ModeOfPathogenicity.objects.create(mode_of_pathogenicity="test")

        self.penetrance = Penetrance.objects.create(penetrance="test")

        self.first_link = PanelGene.objects.create(
            panel=self.first_panel,
            gene=self.first_gene,
            confidence_id=self.confidence.id,
            moi_id=self.moi.id,
            mop_id=self.mop.id,
            penetrance_id=self.penetrance.id,
            justification="PanelApp",
        )

        self.second_link = PanelGene.objects.create(
            panel=self.first_panel,
            gene=self.second_gene,
            confidence_id=self.confidence.id,
            moi_id=self.moi.id,
            mop_id=self.mop.id,
            penetrance_id=self.penetrance.id,
            justification="PanelApp",
        )

    def test_that_low_confidence_gene_are_flagged(self):
        """
        example scenario:
        panel A have existing panel-gene interaction with gene A and gene B
        panel A in the latest PanelApp have only gene A while gene B is removed (confidence less than 3)

        test that `insert_gene` will flag panel A - gene B link (`pending` = True)
        """
        test_panel = PanelClass(
            id="1141",
            name="Acute rhabdomyolyosis",
            version="1.15",
            panel_source="PanelApp",
            genes=[
                {
                    "gene_data": {
                        "hgnc_id": 21497,
                        "gene_name": "acyl-CoA dehydrogenase family member 9",
                        "gene_symbol": "ACAD9",
                        "alias": ["NPD002", "MGC14452"],
                    },
                    "confidence_level": 3,
                    "mode_of_inheritance": "test",
                    "mode_of_pathogenicity": "test",
                    "penetrance": "test",
                },
                {
                    "gene_data": {
                        "hgnc_id": 89,
                        "gene_name": "medium-chain acyl-CoA dehydrogenase",
                        "gene_symbol": "ACADM",
                        "alias": ["MCAD", "MCADH", "ACAD1"],
                    },
                    "confidence_level": 2,  # notice the confidence level
                    "mode_of_inheritance": "test",
                    "mode_of_pathogenicity": "test",
                    "penetrance": "test",
                },
            ],
            regions=[],
        )

        _insert_gene(
            test_panel, self.first_panel, False
        )  # False because this is an existing Panel in the database

        all_genes = Gene.objects.all()
        if not len(all_genes) == 2:
            self.errors.append("There should be two genes in the database")

        all_panel_genes = PanelGene.objects.all()
        if not len(all_panel_genes) == 2:
            self.errors.append("There should be two panel-gene links in the database")

        all_panels = Panel.objects.all()
        if not len(all_panels) == 1:
            self.errors.append("There should be one panel in the database")

        panel_gene_1 = PanelGene.objects.get(
            panel_id=self.first_panel.id, gene_id=self.first_gene.id
        )
        if panel_gene_1.pending:
            self.errors.append("Panel-gene 1 should not be flagged")

        panel_gene_2 = PanelGene.objects.get(
            panel_id=self.first_panel.id, gene_id=self.second_gene.id
        )
        if not panel_gene_2.pending:
            self.errors.append(
                "Panel-gene 2 should be flagged"
            )  # second panel-gene should be flagged

        # check history record
        if not PanelGeneHistory.objects.all().count() == 1:
            self.errors.append("There should only be one history record")
        
        if not PanelGeneHistory.objects.get(panel_gene_id=panel_gene_2.id).note == History.panel_gene_flagged(2):
            self.errors.append("The history record is not correct")

        assert not self.errors, self.errors
