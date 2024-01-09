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


class EvaluatedBy(models.Model):
    """Records who performed evaluation"""

    group = models.TextField(verbose_name="Evaluated by")

    class Meta:
        db_table = "evaluated_by"

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


class Interpretation(models.Model):
    """Records interpretations"""

    individual_id = models.ForeignKey(
        Individual, verbose_name="Individual ID", on_delete=models.PROTECT
    )

    clinical_indication_id = models.ForeignKey(
        ClinicalIndication,
        verbose_name="Clinical Indication ID",
        on_delete=models.PROTECT,
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

    evaluated_by_id = models.ForeignKey(
        EvaluatedBy, verbose_name="Evaluated By ID", on_delete=models.PROTECT
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

    class Meta:
        db_table = "interpretation"

    def __str__(self):
        return str(self.id)
