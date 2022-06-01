#!usr/bin/env python


"""

Git repo at:
https://github.com/Jay-Miles/panels_project/tree/dev

"""


from django.db import models


class ClinicalIndication(models.Model):
    """ Defines a single clinical indication """

    id = models.AutoField(primary_key = True)

    code =  models.CharField(verbose_name='CI code', max_length = 10)

    name = models.TextField(verbose_name='CI name')

    gemini_name = models.TextField(verbose_name='Gemini name')

    source = models.TextField(verbose_name='CI source')

    def __str__(self):
        return self.id


class ClinicalIndicationSource(models.Model):
    """ Defines a source for a clinical indication """

    id = models.AutoField(primary_key = True)

    clinical_indication_id = models.ForeignKey(
        ClinicalIndication,
        verbose_name='Clinical indication',
        on_delete=models.CASCADE)

    source = models.TextField(verbose_name='Source name')

    date = models.CharField(verbose_name='Date', max_length = 10)

    def __str__(self):
        return self.id


class ReferenceGenome(models.Model):
    """ Defines a reference genome build """

    id = models.AutoField(primary_key = True)

    reference_build = models.CharField(
        verbose_name='Genome build',
        max_length = 10)

    def __str__(self):
        return self.id


class Panel(models.Model):
    """ Defines a single internal panel """

    id = models.AutoField(primary_key = True)

    external_id = models.TextField(verbose_name='External panel ID')

    source = models.TextField(verbose_name='Panel source')

    version = models.CharField(verbose_name='Panel version', max_length = 10)

    reference_genome_id = models.ForeignKey(
        ReferenceGenome,
        verbose_name='Reference genome ID',
        on_delete=models.CASCADE)

    def __str__(self):
        return self.id


class ClinicalIndicationPanel(models.Model):
    """ Defines an association between a clinical indication and a panel """

    id = models.AutoField(primary_key = True)

    clinical_indication_id = models.ForeignKey(
        ClinicalIndication,
        verbose_name='Clinical indication',
        on_delete=models.CASCADE)

    panel_id = models.ForeignKey(
        Panel,
        verbose_name='Panel',
        on_delete=models.CASCADE)

    current = models.BooleanField(verbose_name='Currently in use')

    def __str__(self):
        return self.id


class ClinicalIndicationPanelUsage(models.Model):
    """ Defines the period of time in which the specified panel is/was
    associated with the specified clinical indication """

    id = models.AutoField(primary_key = True)

    clinical_indication_panel_id = models.ForeignKey(
        ClinicalIndicationPanel,
        verbose_name='Clinical indication',
        on_delete=models.CASCADE)

    start_date = models.CharField(verbose_name='Start date', max_length = 10)

    end_date = models.BooleanField(verbose_name='Currently in use')

    def __str__(self):
        return self.id


class Hgnc(models.Model):
    """ Defines a single HGNC ID (for a gene) """

    id = models.AutoField(primary_key = True)

    def __str__(self):
        return self.id


class Gene(models.Model):
    """ Defines a single gene by its HGNC ID """

    id = models.AutoField(primary_key = True)

    hgnc_id = models.ForeignKey(
        Hgnc,
        verbose_name='HGNC ID',
        on_delete=models.CASCADE)

    def __str__(self):
        return self.id


class Confidence(models.Model):
    """ Defines the confidence level with which a gene or region is
    associated with a panel """

    id = models.AutoField(primary_key = True)

    confidence_level = models.IntegerField(verbose_name = 'Confidence level')

    def __str__(self):
        return self.id


class Penetrance(models.Model):
    """ Defines the penetrance of the associated phenotype in the
    context of the associated clinical indication """

    id = models.AutoField(primary_key = True)

    penetrance = models.TextField(verbose_name = 'Penetrance')

    def __str__(self):
        return self.id


class ModeOfInheritance(models.Model):
    """ Defines the mode of inheritance of the associated phenotype in
    the context of the associated clinical indication """

    id = models.AutoField(primary_key = True)

    mode_of_inheritance = models.TextField(
        verbose_name = 'Mode of inheritance')

    def __str__(self):
        return self.id


class ModeOfPathogenicity(models.Model):
    """ Defines the mode of pathogenicity of the associated phenotype in
    the context of the associated clinical indication """

    id = models.AutoField(primary_key = True)

    mode_of_pathogenicity = models.TextField(
        verbose_name = 'Mode of pathogenicity')

    def __str__(self):
        return self.id


class PanelGene(models.Model):
    """ Defines a link between a single panel and a single gene """

    id = models.AutoField(primary_key = True)

    panel_id = models.ForeignKey(
        Panel,
        verbose_name='Panel ID',
        on_delete=models.CASCADE)

    gene_id = models.ForeignKey(
        Gene,
        verbose_name='Gene ID',
        on_delete=models.CASCADE)

    confidence_id = models.ForeignKey(
        Confidence,
        verbose_name='Confidence ID',
        on_delete=models.CASCADE)

    moi_id = models.ForeignKey(
        ModeOfInheritance,
        verbose_name='Mode of inheritance ID',
        on_delete=models.CASCADE)

    mop_id = models.ForeignKey(
        ModeOfPathogenicity,
        verbose_name='Mode of pathogenicity ID',
        on_delete=models.CASCADE)

    penetrance_id = models.ForeignKey(
        Penetrance,
        verbose_name='Penetrance ID',
        on_delete=models.CASCADE)

    justification = models.TextField(verbose_name = 'Justification')

    def __str__(self):
        return self.id


class Transcript(models.Model):
    """ Defines a single transcript by RefSeq ID """

    id = models.AutoField(primary_key = True)

    refseq_id = models.CharField(verbose_name = 'RefSeq ID', max_length = 20)

    def __str__(self):
        return self.id


class PanelGeneTranscript(models.Model):
    """ Defines a link between a single transcript and a single gene, in
    the context of a specific panel """

    id = models.AutoField(primary_key = True)

    panel_gene_id = models.ForeignKey(
        PanelGene,
        verbose_name='Panel/gene link ID',
        on_delete=models.CASCADE)

    transcript_id = models.ForeignKey(
        Transcript,
        verbose_name='Transcript ID',
        on_delete=models.CASCADE)

    justification = models.TextField(verbose_name = 'justification')

    def __str__(self):
        return self.id


class Haploinsufficiency(models.Model):
    """ Defines the haploinsufficiency score of the associated phenotype
    in the context of the associated clinical indication """

    id = models.AutoField(primary_key = True)

    haploinsufficiency = models.IntegerField(
        verbose_name = 'Haploinsufficiency score')

    def __str__(self):
        return self.id


class Triplosensitivity(models.Model):
    """ Defines the triplosensitivity score of the associated phenotype
    in the context of the associated clinical indication """

    id = models.AutoField(primary_key = True)

    triplosensitivity = models.IntegerField(
        verbose_name = 'Triplosensitivity score')

    def __str__(self):
        return self.id


class RequiredOverlap(models.Model):
    """ GEL internal field relating to CNV detection method """

    id = models.AutoField(primary_key = True)

    required_overlap = models.IntegerField(
        verbose_name = 'Required percent overlap')

    def __str__(self):
        return self.id


class VariantType(models.Model):
    """ Defines the type of variant  """

    id = models.AutoField(primary_key = True)

    variant_type = models.CharField(
        verbose_name = 'Variant type',
        max_length = 10)

    def __str__(self):
        return self.id


class Region(models.Model):
    """ Defines a single region (CNV) """

    id = models.AutoField(primary_key = True)

    name = models.CharField(verbose_name = 'Region name', max_length = 20)

    chrom = models.CharField(verbose_name = 'Chromosome', max_length = 5)

    start = models.IntegerField(verbose_name = 'Region start')

    end = models.IntegerField(verbose_name = 'Region end')

    def __str__(self):
        return self.id


class PanelRegion(models.Model):
    """ Defines a link between a single panel and a single region """

    id = models.AutoField(primary_key = True)

    panel_id = models.ForeignKey(
        Panel,
        verbose_name='Panel ID',
        on_delete=models.CASCADE)

    confidence_id = models.ForeignKey(
        Confidence,
        verbose_name='Confidence level ID',
        on_delete=models.CASCADE)

    moi_id = models.ForeignKey(
        ModeOfInheritance,
        verbose_name='Mode of inheritance ID',
        on_delete=models.CASCADE)

    mop_id = models.ForeignKey(
        ModeOfPathogenicity,
        verbose_name='Mode of pathogenicity ID',
        on_delete=models.CASCADE)

    penetrance_id = models.ForeignKey(
        Penetrance,
        verbose_name='Penetrance ID',
        on_delete=models.CASCADE)

    region_id = models.ForeignKey(
        Region,
        verbose_name='Region ID',
        on_delete=models.CASCADE)

    haplo_id = models.ForeignKey(
        Haploinsufficiency,
        verbose_name='Haploinsufficiency ID',
        on_delete=models.CASCADE)

    triplo_id = models.ForeignKey(
        Triplosensitivity,
        verbose_name='Triplosensitivity ID',
        on_delete=models.CASCADE)

    overlap_id = models.ForeignKey(
        RequiredOverlap,
        verbose_name='Required overlap ID',
        on_delete=models.CASCADE)

    vartype_id = models.ForeignKey(
        VariantType,
        verbose_name='Variant type ID',
        on_delete=models.CASCADE)

    justification = models.TextField(verbose_name = 'Justification')

    def __str__(self):
        return self.id


class RegionAnnotation(models.Model):
    """ Define an annotation for a region """

    id = models.AutoField(primary_key = True)

    region_id = models.ForeignKey(
        Region,
        verbose_name='Region ID',
        on_delete=models.CASCADE)

    attribute = models.TextField(verbose_name = 'Attribute')

    value = models.TextField(verbose_name = 'Value')

    timestamp = models.DateTimeField(verbose_name = 'Timestamp')

    source = models.TextField(verbose_name = 'Source')

    def __str__(self):
        return self.id
