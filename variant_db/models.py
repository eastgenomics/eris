from django.db import models
from panels_backend.models import Chromosome, ClinicalIndication, Panel, ReferenceGenome

# Create your models here.


class Sample(models.Model):
    """
    Records samples which have undergone sequencing.
    A particular combination of specimen, batch, and instrument SHOULD be unique.
    We store this because we want to make sure that data from a single sample isn't accidentally
    submitted multiple times.
    """

    instrument_id = models.TextField(verbose_name="Instrument ID")

    batch_id = models.TextField(verbose_name="Batch ID")

    specimen_id = models.TextField(verbose_name="Specimen ID")

    class Meta:
        db_table = "sample"
        unique_together = ["instrument_id", "batch_id", "specimen_id"]

    def __str__(self):
        return str(self.id)


class TestCode(models.Model):
    """The code of the test used when sequencing a sample. Assay-specific"""

    testcode = models.TextField(verbose_name="Test code")

    class Meta:
        db_table = "test_code"

    def __str__(self):
        return str(self.id)


class ProbeSet(models.Model):
    """
    The specific probeset used when sequencing a sample. A particular test's probes
    may change over time
    """

    probeset_id = models.TextField(verbose_name="Probeset ID")

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

    name = models.TextField(verbose_name="Affected status")

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

    name = models.TextField(verbose_name="Assertion criteria name")

    class Meta:
        db_table = "assertion_criteria"

    def __str__(self):
        return str(self.id)


class ClinicalSignificanceDescription(models.Model):
    """
    Records clinical significance descriptions
    Example values: 'Pathogenic', 'Benign'
    """

    category = models.TextField(verbose_name="CSD category")

    class Meta:
        db_table = "clinical_significance_description"

    def __str__(self):
        return str(self.id)


class AssayMethod(models.Model):
    """Records assay methods"""

    name = models.TextField(verbose_name="Assay method name")

    class Meta:
        db_table = "assay_method"

    def __str__(self):
        return str(self.id)


class ClinvarCollectionMethod(models.Model):
    """
    Records clinvar collection methods.
    Examples of permitted values: 'clinical testing' 'case-control'
    """

    name = models.TextField(verbose_name="Clinvar collection method name")

    class Meta:
        db_table = "clinvar_collection_method"

    def __str__(self):
        return str(self.id)


class Variant(models.Model):
    """
    Records variants
    """

    interpreted = models.BooleanField(verbose_name="Interpreted by scientist")

    reference_genome_id = models.ForeignKey(
        ReferenceGenome, verbose_name="Reference Genome ID", on_delete=models.PROTECT
    )

    chromosome_id = models.ForeignKey(
        Chromosome, verbose_name="Chromosome ID", on_delete=models.PROTECT
    )

    position = models.IntegerField(verbose_name="Variant Position")

    ref = models.TextField(
        verbose_name="Reference variant allele"
    )  # what's the maximum variant size?

    alt = models.TextField(verbose_name="Alternative variant allele")  # see above

    class Meta:
        db_table = "variant"

    def __str__(self):
        return str(self.id)


class ClinvarAlleleOrigin(models.Model):
    """
    Records clinvar allele origins
    The genetic origin of the variant - example values: 'de novo', 'germline', 'somatic', 'maternal'
    """

    category = models.TextField(verbose_name="Allele origin")

    class Meta:
        db_table = "clinvar_allele_origin"

    def __str__(self):
        return str(self.id)


class ClinvarSubmission(models.Model):
    """Records clinvar submissions"""

    scv_id = models.TextField(verbose_name="SCV ID")

    scv_id_version = models.TextField(verbose_name="SCV ID version")

    submission_id = models.TextField(verbose_name="ClinVar submission ID")

    submission_date = models.DateTimeField(verbose_name="Submission timestamp")

    class Meta:
        db_table = "clinvar_submission"

    def __str__(self):
        return str(self.id)


class Organization(models.Model):
    """
    The name of the Organization where the interpretation was carried out
    Generally larger than an Institution. For example, a GLH would be an Organization.
    #TODO: write an Organization/Institution relationship once it emerges?
    """

    name = models.TextField(verbose_name="Organization name")

    class Meta:
        db_table = "organization"

    def __str__(self):
        return str(self.id)


class Institution(models.Model):
    """
    The name of the Institution where the interpretation was carried out
    Generally smaller than an Organization. For example, a hospital which is part of a GLH would be an Institution.
    """

    name = models.TextField(verbose_name="Institution name")

    class Meta:
        db_table = "institution"

    def __str__(self):
        return str(self.id)


class Interpretation(models.Model):
    """
    Records interpretations - information which is linked to the process of assessing the clinical significance of a finding
    """

    sample_id = models.ForeignKey(
        Sample, verbose_name="Sample ID", on_delete=models.PROTECT
    )

    # TODO: long term, switch to using ClinicalIndication as an FK here. For now, tolerate strings.
    # N.B. this is NOT a ClinicalIndication FK.
    clinical_indication = models.TextField(
        verbose_name="Clinical indication as it appears in parsed results workbook"
    )

    affected_status_id = models.ForeignKey(
        AffectedStatus, verbose_name="Affected Status ID", on_delete=models.PROTECT
    )

    assertion_criteria_id = models.ForeignKey(
        AssertionCriteria,
        verbose_name="Assertion Criteria ID",
        on_delete=models.PROTECT,
    )

    clinical_significance_description_id = models.ForeignKey(
        ClinicalSignificanceDescription,
        verbose_name="Clinical Significance Description ID",
        on_delete=models.PROTECT,
    )

    evaluating_organization = models.ForeignKey(
        Organization,
        verbose_name="Evaluating Organization ID",
        on_delete=models.PROTECT,
    )

    evaluating_institution = models.ForeignKey(
        Institution, verbose_name="Evaluating Institution ID", on_delete=models.PROTECT
    )

    panel_id = models.ForeignKey(
        Panel, verbose_name="Panel ID", on_delete=models.PROTECT
    )

    assay_method_id = models.ForeignKey(
        AssayMethod, verbose_name="Assay Method ID", on_delete=models.PROTECT
    )

    clinvar_collection_method_id = models.ForeignKey(
        ClinvarCollectionMethod,
        verbose_name="Clinvar Collection Method ID",
        on_delete=models.PROTECT,
    )

    variant_id = models.ForeignKey(
        Variant, verbose_name="Variant ID", on_delete=models.PROTECT
    )

    clinvar_allele_origin_id = models.ForeignKey(
        ClinvarAlleleOrigin,
        verbose_name="Clinvar Allele Origin ID",
        on_delete=models.PROTECT,
    )

    clinvar_submission_id = models.ForeignKey(
        ClinvarSubmission,
        verbose_name="Clinvar Submission ID",
        on_delete=models.PROTECT,
    )

    prevalence = models.TextField(verbose_name="Prevalence of variant")

    # Inheritance pattern. Not to be confused with ModeOfInheritance, which is populated from PanelApp for PanelGene/SuperPanelGene
    known_inheritance = models.TextField(
        verbose_name="Inheritance pattern",
    )

    associated_disease = models.TextField(verbose_name="Associated disease")

    probe_set = models.ForeignKey(
        ProbeSet,
        verbose_name="Probe set used for sequencing",
        on_delete=models.PROTECT,
    )

    # TODO: this is in review in the sample sheet side of things
    date = models.DateField(verbose_name="Interpretation date")

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

    PVS1_verdict = models.TextField(verbose_name="PSV1 verdict", nullable=True)
    PSV1_evidence = models.TextField(verbose_name="PSV1 evidence notes", nullable=True)

    PS1_verdict = models.TextField(verbose_name="PS1 verdict", nullable=True)
    PS1_evidence = models.TextField(verbose_name="PS1 evidence notes", nullable=True)

    PS2_verdict = models.TextField(verbose_name="PS2 verdict", nullable=True)
    PS2_evidence = models.TextField(verbose_name="PS2 evidence notes", nullable=True)

    PS3_verdict = models.TextField(verbose_name="PS3 verdict", nullable=True)
    PS3_evidence = models.TextField(verbose_name="PS3 evidence notes", nullable=True)

    PS4_verdict = models.TextField(verbose_name="PS4 verdict", nullable=True)
    PS4_evidence = models.TextField(verbose_name="PS4 evidence notes", nullable=True)

    PM1_verdict = models.TextField(verbose_name="PM1 verdict", nullable=True)
    PM1_evidence = models.TextField(verbose_name="PM1 evidence notes", nullable=True)

    PM2_verdict = models.TextField(verbose_name="PM2 verdict", nullable=True)
    PM2_evidence = models.TextField(verbose_name="PM2 evidence notes", nullable=True)

    PM3_verdict = models.TextField(verbose_name="PM3 verdict", nullable=True)
    PM3_evidence = models.TextField(verbose_name="PM3 evidence notes", nullable=True)

    PM4_verdict = models.TextField(verbose_name="PM4 verdict", nullable=True)
    PM4_evidence = models.TextField(verbose_name="PM4 evidence notes", nullable=True)

    PM5_verdict = models.TextField(verbose_name="PM5 verdict", nullable=True)
    PM5_evidence = models.TextField(verbose_name="PM5 evidence notes", nullable=True)

    PM6_verdict = models.TextField(verbose_name="PM6 verdict", nullable=True)
    PM6_evidence = models.TextField(verbose_name="PM6 evidence notes", nullable=True)

    PP1_verdict = models.TextField(verbose_name="PP1 verdict", nullable=True)
    PP1_evidence = models.TextField(verbose_name="PP1 evidence notes", nullable=True)

    PP2_verdict = models.TextField(verbose_name="PP2 verdict", nullable=True)
    PP2_evidence = models.TextField(verbose_name="PP2 evidence notes", nullable=True)

    PP3_verdict = models.TextField(verbose_name="PP3 verdict", nullable=True)
    PP3_evidence = models.TextField(verbose_name="PP3 evidence notes", nullable=True)

    PP4_verdict = models.TextField(verbose_name="PP4 verdict", nullable=True)
    PP4_evidence = models.TextField(verbose_name="PP4 evidence notes", nullable=True)

    PP5_verdict = models.TextField(verbose_name="PP5 verdict", nullable=True)
    PP5_evidence = models.TextField(verbose_name="PP5 evidence notes", nullable=True)

    BS1_verdict = models.TextField(verbose_name="BS1 verdict", nullable=True)
    BS1_evidence = models.TextField(verbose_name="BS1 evidence notes", nullable=True)

    BS2_verdict = models.TextField(verbose_name="BS2 verdict", nullable=True)
    BS2_evidence = models.TextField(verbose_name="BS2 evidence notes", nullable=True)

    BS3_verdict = models.TextField(verbose_name="BS3 verdict", nullable=True)
    BS3_evidence = models.TextField(verbose_name="BS3 evidence notes", nullable=True)

    BS4_verdict = models.TextField(verbose_name="BS4 verdict", nullable=True)
    BS4_evidence = models.TextField(verbose_name="BS4 evidence notes", nullable=True)

    BA1_verdict = models.TextField(verbose_name="BA1 verdict", nullable=True)
    BA1_evidence = models.TextField(verbose_name="BA1 evidence notes", nullable=True)

    BP1_verdict = models.TextField(verbose_name="BP1 verdict", nullable=True)
    BP1_evidence = models.TextField(verbose_name="BP1 evidence notes", nullable=True)

    BP2_verdict = models.TextField(verbose_name="BP2 verdict", nullable=True)
    BP2_evidence = models.TextField(verbose_name="BP2 evidence notes", nullable=True)

    BP3_verdict = models.TextField(verbose_name="BP3 verdict", nullable=True)
    BP3_evidence = models.TextField(verbose_name="BP3 evidence notes", nullable=True)

    BP4_verdict = models.TextField(verbose_name="BP4 verdict", nullable=True)
    BP4_evidence = models.TextField(verbose_name="BP4 evidence notes", nullable=True)

    BP5_verdict = models.TextField(verbose_name="BP5 verdict", nullable=True)
    BP5_evidence = models.TextField(verbose_name="BP5 evidence notes", nullable=True)

    BP6_verdict = models.TextField(verbose_name="BP6 verdict", nullable=True)
    BP6_evidence = models.TextField(verbose_name="BP6 evidence notes", nullable=True)

    BP7_verdict = models.TextField(verbose_name="BP7 verdict", nullable=True)
    BP7_evidence = models.TextField(verbose_name="BP7 evidence notes", nullable=True)

    class Meta:
        db_table = "acgs_category_information"

    def __str__(self):
        return str(self.id)