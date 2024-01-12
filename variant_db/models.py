from django.db import models
from panels_backend.models import Chromosome, ClinicalIndication, Panel, ReferenceGenome

# Create your models here.

class Individual(models.Model):
    """Records individuals"""

    individual_identifier = models.TextField(verbose_name="Individual external ID")

    class Meta:
        db_table = "individual"

    def __str__(self):
        return str(self.id)


class TestCode(models.Model):
    """The code of the test used when sequencing a sample. Assay-specific"""
    testcode = models.TextField(
        verbose_name="Test code"
    )
    class Meta:
        db_table = "test_code"

    def __str__(self):
        return str(self.id)


class ProbeSet(models.Model):
    """
    The specific probeset used when sequencing a sample. A particular test's probes
    may change over time
    """
    probeset_id = models.TextField(
        verbose_name="Probeset ID"
    )

    testcode = models.ForeignKey(
        TestCode,
        verbose_name="Test code", 
        on_delete=models.PROTECT
        )

    class Meta:
        db_table = "probeset"

    def __str__(self):
        return str(self.id)


class AffectedStatus(models.Model):
    """Records affected statuses"""

    name = models.TextField(verbose_name="Affected status")

    class Meta:
        db_table = "affected_status"

    def __str__(self):
        return str(self.id)


class AssertionCriteria(models.Model):
    """Records assertion criteria"""

    name = models.TextField(verbose_name="Assertion criteria name")

    class Meta:
        db_table = "assertion_criteria"

    def __str__(self):
        return str(self.id)


class ClinicalSignificanceDescription(models.Model):
    """Records clinical significance descriptions"""

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
    """Records clinvar collection methods"""

    name = models.TextField(verbose_name="Clinvar collection method name")

    class Meta:
        db_table = "clinvar_collection_method"

    def __str__(self):
        return str(self.id)


class Variant(models.Model):
    """Records variants"""
    interpreted = models.BooleanField(
        verbose_name="Interpreted by scientist"
    )

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
    """Records clinvar allele origins"""

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


class Organisation(models.Model):
    """
    The name of the Organisation where the interpretation was carried out
    Generally larger than an Institution. For example, a GLH would be an Organisation.
    #TODO: write an Organisation/Institution relationship once it emerges
    """
    name = models.TextField(verbose_name="Organisation name")

    class Meta:
        db_table = "organisation"

    def __str__(self):
        return str(self.id)

class Institution(models.Model):
    """
    The name of the Institution where the interpretation was carried out
    Generally smaller than an Organisation. For example, a hospital which is part of a GLH would be an Institution.
    """
    name = models.TextField(verbose_name="Institution name")

    class Meta:
        db_table = "institution"

    def __str__(self):
        return str(self.id)
    
class Interpretation(models.Model):
    """Records interpretations"""

    individual_id = models.ForeignKey(
        Individual, verbose_name="Individual ID", on_delete=models.PROTECT
    )

    #TODO: long term, switch to using ClinicalIndication as an FK here. For now, tolerate strings.
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

    evaluating_organisation = models.ForeignKey(
        Organisation, verbose_name="Evaluating Organisation ID", on_delete=models.PROTECT
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

    prevalence = models.TextField(
        verbose_name="Prevalence of variant"
    )

    # Inheritance pattern. Not to be confused with ModeOfInheritance, which is populated from PanelApp for PanelGene/SuperPanelGene
    known_inheritance = models.TextField(
        verbose_name="Inheritance pattern",
    )

    associated_disease = models.TextField(
        verbose_name="Associated disease"
    )

    probe_set = models.ForeignKey(
        ProbeSet,
        verbose_name="Probe set used for sequencing",
        on_delete=models.PROTECT,
    )

    #TODO: this is in review in the sample sheet side of things
    date = models.DateField(
        verbose_name="Interpretation date"
    )

    class Meta:
        db_table = "interpretation"

    def __str__(self):
        return str(self.id)
