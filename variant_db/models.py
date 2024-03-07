from django.db import models
from panels_backend.models import (
    Panel,
    ReferenceGenome,
)


class Sample(models.Model):
    """
    Records samples which have undergone sequencing.
    A particular combination of specimen, batch, and instrument SHOULD be unique.
    We store this because we want to make sure that data from a single sample isn't accidentally
    submitted multiple times.
    """

    instrument_id = models.TextField(verbose_name="Instrument ID", null=False)

    batch_id = models.TextField(verbose_name="Batch ID", null=False)

    specimen_id = models.TextField(verbose_name="Specimen ID", null=False)

    class Meta:
        db_table = "sample"
        unique_together = ["instrument_id", "batch_id", "specimen_id"]

    def __str__(self):
        return str(self.id)


class TestCode(models.Model):
    """The code of the test used when sequencing a sample. Assay-specific"""

    test_code = models.TextField(verbose_name="Test code", null=False)

    class Meta:
        db_table = "test_code"

    def __str__(self):
        return str(self.id)


class ProbeSet(models.Model):
    """
    The specific probeset used when sequencing a sample. A particular test's probes
    may change over time
    """

    probeset_id = models.TextField(verbose_name="Probeset ID", null=False)

    testcode = models.ForeignKey(
        TestCode, verbose_name="Test code", on_delete=models.PROTECT
    )

    class Meta:
        db_table = "probeset"

    def __str__(self):
        return str(self.id)


class AffectedStatus(models.Model):
    """
    Records affected statuses - whether or not the individual in each observation was affected by the condition
    for the interpretation.
    Example values: yes, no, unknown
    """

    name = models.TextField(verbose_name="Affected status", null=True)

    class Meta:
        db_table = "affected_status"

    def __str__(self):
        return str(self.id)


class AssertionCriteria(models.Model):
    """
    Records assertion criteria.
    This can be something like ACGS Best Practice Guidelines for Variant Interpretation 2020,
    a condition-specific set of guidelines, or something like a Pubmed ID.
    """

    category = models.TextField(
        verbose_name="Assertion criteria name", null=True
    )

    class Meta:
        db_table = "assertion_criteria"

    def __str__(self):
        return str(self.id)


class ClinicalSignificanceDescription(models.Model):
    """
    Records clinical significance descriptions
    Example values: 'Pathogenic', 'Benign'
    """

    category = models.TextField(verbose_name="CSD category", null=True)

    class Meta:
        db_table = "clinical_significance_description"

    def __str__(self):
        return str(self.id)


class AssayMethod(models.Model):
    """Records assay methods"""

    name = models.TextField(verbose_name="Assay method name", null=True)

    class Meta:
        db_table = "assay_method"

    def __str__(self):
        return str(self.id)


class ClinvarCollectionMethod(models.Model):
    """
    Records clinvar collection methods.
    Examples of permitted values: 'clinical testing' 'case-control'
    """

    name = models.TextField(
        verbose_name="Clinvar collection method name", null=True
    )

    class Meta:
        db_table = "clinvar_collection_method"

    def __str__(self):
        return str(self.id)


class Chromosome(models.Model):
    """
    Records chromosomes
    """

    name = models.TextField(verbose_name="chromosome name", null=False)

    numerical_name = models.IntegerField(
        verbose_name="numeric index"
    )  # Intended to be prepopulated by admin (i.e. reference data that the user shouldn't change)

    source = models.TextField(
        verbose_name="chromosome source (i.e. RefSeq, Assembly, Genbank etc.)"  # Prepopulated (as above)
    )

    class Meta:
        db_table = "chromosome"

    def __str__(self):
        return str(self.id)


class Variant(models.Model):
    """
    Records variants
    """

    interpreted = models.BooleanField(
        verbose_name="Interpreted by scientist", null=True
    )

    reference_genome = models.ForeignKey(
        ReferenceGenome,
        verbose_name="Reference Genome ID",
        on_delete=models.PROTECT,
        null=False,
    )

    chromosome = models.ForeignKey(
        Chromosome,
        verbose_name="Chromosome ID",
        on_delete=models.PROTECT,
        null=False,
    )

    start = models.IntegerField(verbose_name="Variant Position", null=False)

    reference_allele = models.TextField(
        verbose_name="Reference variant allele", null=False
    )

    alternate_allele = models.TextField(
        verbose_name="Alternative variant allele", null=False
    )

    hgvsc = models.TextField(verbose_name="HGVS c.dot notation", null=False)

    class Meta:
        db_table = "variant"

    def __str__(self):
        return str(self.id)


class ClinvarAlleleOrigin(models.Model):
    """
    Records clinvar allele origins
    The genetic origin of the variant - example values: 'de novo', 'germline', 'somatic', 'maternal'
    """

    category = models.TextField(verbose_name="Allele origin", null=True)

    class Meta:
        db_table = "clinvar_allele_origin"

    def __str__(self):
        return str(self.id)


class ClinvarSubmission(models.Model):
    """Records clinvar submissions"""

    scv_id = models.TextField(verbose_name="SCV ID", null=True)

    scv_id_version = models.TextField(verbose_name="SCV ID version", null=True)

    submission_id = models.TextField(
        verbose_name="ClinVar submission ID", null=True
    )

    submission_date = models.DateTimeField(
        verbose_name="Submission timestamp", null=True
    )

    class Meta:
        db_table = "clinvar_submission"

    def __str__(self):
        return str(self.id)


class Organization(models.Model):
    """
    The name of the Organization where the interpretation was carried out
    Generally larger than an Institution. For example, a GLH would be an Organization.
    """

    name = models.TextField(verbose_name="Organization name", null=True)

    external_id = models.IntegerField(
        verbose_name="Organization external ID", null=True
    )

    class Meta:
        db_table = "organization"

    def __str__(self):
        return str(self.id)


class Institution(models.Model):
    """
    The name of the Institution where the interpretation was carried out
    Generally smaller than an Organization. For example, a hospital which is part of a GLH would be an Institution.
    """

    name = models.TextField(verbose_name="Institution name", null=True)

    class Meta:
        db_table = "institution"

    def __str__(self):
        return str(self.id)


class Interpretation(models.Model):
    """
    Records interpretations - information which is linked to the process of assessing the clinical significance of a finding
    """

    sample = models.ForeignKey(
        Sample, verbose_name="Sample ID", on_delete=models.PROTECT
    )

    # TODO: long term, switch to using ClinicalIndication as an FK here. For now, tolerate strings.
    # N.B. this is NOT a ClinicalIndication FK.
    preferred_condition_name = models.TextField(
        verbose_name="Clinical indication as it appears in parsed results workbook"
    )

    affected_status = models.ForeignKey(
        AffectedStatus,
        verbose_name="Affected Status ID",
        on_delete=models.PROTECT,
    )

    preferred_condition_name = models.CharField(
        verbose_name="Long-form alias for condition", null=False
    )

    assertion_criteria = models.ForeignKey(
        AssertionCriteria,
        verbose_name="Assertion Criteria ID",
        on_delete=models.PROTECT,
    )

    clinical_significance_description = models.ForeignKey(
        ClinicalSignificanceDescription,
        verbose_name="Clinical Significance Description ID",
        on_delete=models.PROTECT,
    )

    clinical_significance_comment = models.CharField(
        verbose_name="Comment on classification", null=True
    )

    evaluating_organization = models.ForeignKey(
        Organization,
        verbose_name="Evaluating Organization ID",
        on_delete=models.PROTECT,
    )

    evaluating_institution = models.ForeignKey(
        Institution,
        verbose_name="Evaluating Institution ID",
        on_delete=models.PROTECT,
    )

    assay_method = models.ForeignKey(
        AssayMethod, verbose_name="Assay Method ID", on_delete=models.PROTECT
    )

    clinvar_collection_method = models.ForeignKey(
        ClinvarCollectionMethod,
        verbose_name="Clinvar Collection Method ID",
        on_delete=models.PROTECT,
    )

    variant = models.ForeignKey(
        Variant, verbose_name="Variant ID", on_delete=models.PROTECT
    )

    clinvar_allele_origin = models.ForeignKey(
        ClinvarAlleleOrigin,
        verbose_name="Clinvar Allele Origin ID",
        on_delete=models.PROTECT,
    )

    clinvar_submission = models.ForeignKey(
        ClinvarSubmission,
        verbose_name="Clinvar Submission ID",
        null=True,
        on_delete=models.PROTECT,
    )

    prevalence = models.TextField(
        verbose_name="Prevalence of variant", null=True
    )

    # Inheritance pattern. Not to be confused with ModeOfInheritance,
    # which is populated from PanelApp for PanelGene/SuperPanelGene
    known_inheritance = models.TextField(
        verbose_name="Inheritance pattern", null=True
    )

    associated_disease = models.TextField(
        verbose_name="Associated disease", null=True
    )

    probe_set = models.ForeignKey(
        ProbeSet,
        verbose_name="Probe set used for sequencing",
        on_delete=models.PROTECT,
    )

    date_last_evaluated = models.DateField(
        verbose_name="Date that the interpretation was completed", null=True
    )

    # by this we mean "from the "Comment" field in the "Included" tab"
    comment_from_included = models.CharField(
        verbose_name='Comment field from workbook "Included" tab', null=True
    )

    class Meta:
        db_table = "interpretation"

    def __str__(self):
        return str(self.id)


class AcgsCategoryInformation(models.Model):
    """
    For variants which undergo ACGS-style categorisation,
    add scores and evidence notes for each of the scoring
    categories.
    """

    interpretation = models.ForeignKey(
        Interpretation, verbose_name="Interpretation", on_delete=models.PROTECT
    )

    PVS1_verdict = models.TextField(verbose_name="PSV1 verdict", null=True)
    PVS1_evidence = models.TextField(
        verbose_name="PSV1 evidence notes", null=True
    )

    PS1_verdict = models.TextField(verbose_name="PS1 verdict", null=True)
    PS1_evidence = models.TextField(
        verbose_name="PS1 evidence notes", null=True
    )

    PS2_verdict = models.TextField(verbose_name="PS2 verdict", null=True)
    PS2_evidence = models.TextField(
        verbose_name="PS2 evidence notes", null=True
    )

    PS3_verdict = models.TextField(verbose_name="PS3 verdict", null=True)
    PS3_evidence = models.TextField(
        verbose_name="PS3 evidence notes", null=True
    )

    PS4_verdict = models.TextField(verbose_name="PS4 verdict", null=True)
    PS4_evidence = models.TextField(
        verbose_name="PS4 evidence notes", null=True
    )

    PM1_verdict = models.TextField(verbose_name="PM1 verdict", null=True)
    PM1_evidence = models.TextField(
        verbose_name="PM1 evidence notes", null=True
    )

    PM2_verdict = models.TextField(verbose_name="PM2 verdict", null=True)
    PM2_evidence = models.TextField(
        verbose_name="PM2 evidence notes", null=True
    )

    PM3_verdict = models.TextField(verbose_name="PM3 verdict", null=True)
    PM3_evidence = models.TextField(
        verbose_name="PM3 evidence notes", null=True
    )

    PM4_verdict = models.TextField(verbose_name="PM4 verdict", null=True)
    PM4_evidence = models.TextField(
        verbose_name="PM4 evidence notes", null=True
    )

    PM5_verdict = models.TextField(verbose_name="PM5 verdict", null=True)
    PM5_evidence = models.TextField(
        verbose_name="PM5 evidence notes", null=True
    )

    PM6_verdict = models.TextField(verbose_name="PM6 verdict", null=True)
    PM6_evidence = models.TextField(
        verbose_name="PM6 evidence notes", null=True
    )

    PP1_verdict = models.TextField(verbose_name="PP1 verdict", null=True)
    PP1_evidence = models.TextField(
        verbose_name="PP1 evidence notes", null=True
    )

    PP2_verdict = models.TextField(verbose_name="PP2 verdict", null=True)
    PP2_evidence = models.TextField(
        verbose_name="PP2 evidence notes", null=True
    )

    PP3_verdict = models.TextField(verbose_name="PP3 verdict", null=True)
    PP3_evidence = models.TextField(
        verbose_name="PP3 evidence notes", null=True
    )

    PP4_verdict = models.TextField(verbose_name="PP4 verdict", null=True)
    PP4_evidence = models.TextField(
        verbose_name="PP4 evidence notes", null=True
    )

    PP5_verdict = models.TextField(verbose_name="PP5 verdict", null=True)
    PP5_evidence = models.TextField(
        verbose_name="PP5 evidence notes", null=True
    )

    BS1_verdict = models.TextField(verbose_name="BS1 verdict", null=True)
    BS1_evidence = models.TextField(
        verbose_name="BS1 evidence notes", null=True
    )

    BS2_verdict = models.TextField(verbose_name="BS2 verdict", null=True)
    BS2_evidence = models.TextField(
        verbose_name="BS2 evidence notes", null=True
    )

    BS3_verdict = models.TextField(verbose_name="BS3 verdict", null=True)
    BS3_evidence = models.TextField(
        verbose_name="BS3 evidence notes", null=True
    )

    BS4_verdict = models.TextField(verbose_name="BS4 verdict", null=True)
    BS4_evidence = models.TextField(
        verbose_name="BS4 evidence notes", null=True
    )

    BA1_verdict = models.TextField(verbose_name="BA1 verdict", null=True)
    BA1_evidence = models.TextField(
        verbose_name="BA1 evidence notes", null=True
    )

    BP1_verdict = models.TextField(verbose_name="BP1 verdict", null=True)
    BP1_evidence = models.TextField(
        verbose_name="BP1 evidence notes", null=True
    )

    BP2_verdict = models.TextField(verbose_name="BP2 verdict", null=True)
    BP2_evidence = models.TextField(
        verbose_name="BP2 evidence notes", null=True
    )

    BP3_verdict = models.TextField(verbose_name="BP3 verdict", null=True)
    BP3_evidence = models.TextField(
        verbose_name="BP3 evidence notes", null=True
    )

    BP4_verdict = models.TextField(verbose_name="BP4 verdict", null=True)
    BP4_evidence = models.TextField(
        verbose_name="BP4 evidence notes", null=True
    )

    BP5_verdict = models.TextField(verbose_name="BP5 verdict", null=True)
    BP5_evidence = models.TextField(
        verbose_name="BP5 evidence notes", null=True
    )

    BP6_verdict = models.TextField(verbose_name="BP6 verdict", null=True)
    BP6_evidence = models.TextField(
        verbose_name="BP6 evidence notes", null=True
    )

    BP7_verdict = models.TextField(verbose_name="BP7 verdict", null=True)
    BP7_evidence = models.TextField(
        verbose_name="BP7 evidence notes", null=True
    )

    class Meta:
        db_table = "acgs_category_information"

    def __str__(self):
        return str(self.id)


class InterpretationPanel(models.Model):
    """
    Interpretation->Panel linking table
    """

    interpretation = models.ForeignKey(
        Interpretation, on_delete=models.PROTECT
    )
    panel = models.ForeignKey(Panel, on_delete=models.PROTECT)

    class Meta:
        db_table = "interpretation_panel"

    def __str__(self):
        return str(self.id)
