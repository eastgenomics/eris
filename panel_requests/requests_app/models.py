#!usr/bin/env python


"""
Git repo at:
https://github.com/eastgenomics/panel_requests/tree/dev
"""


from django.db import models


class ReferenceGenome(models.Model):
    """ Defines a reference genome build """

    reference_build = models.CharField(
        verbose_name = 'Genome build',
        max_length = 255,
        unique = True,)

    class Meta:
        db_table = 'reference_genome'

    def __str__(self):
        return str(self.id)


class Panel(models.Model):
    """ Defines a single internal panel """

    external_id = models.TextField(
        verbose_name='External panel ID',
        max_length = 255,)

    panel_source = models.TextField(
        verbose_name='Panel source',
        max_length = 255,)

    panel_version = models.CharField(
        verbose_name='Panel version',
        max_length = 255,)

    reference_genome = models.ForeignKey(
        ReferenceGenome,
        verbose_name = 'Reference genome ID',
        on_delete = models.PROTECT,)

    class Meta:
        db_table = 'panel'

    def __str__(self):
        return str(self.id)


class CiPanelAssociationSource(models.Model):
    """ Defines a source for the association between a specific clinical
    indication and a specific panel """

    source = models.TextField(verbose_name = 'Source name', max_length = 255,)
    date = models.DateField(verbose_name = 'Date')

    class Meta:
        db_table = 'ci_panel_association_source'

    def __str__(self):
        return str(self.id)


class ClinicalIndication(models.Model):
    """ Defines a single clinical indication """

    code = models.CharField(verbose_name = 'CI code', max_length = 255,)
    name = models.TextField(verbose_name = 'CI name', max_length = 255,)

    gemini_name = models.TextField(
        verbose_name = 'Gemini name',
        max_length = 255,)

    class Meta:
        db_table = 'clinical_indication'

    def __str__(self):
        return str(self.id)


class ClinicalIndicationPanel(models.Model):
    """ Defines an association between a clinical indication and a panel """

    source = models.ForeignKey(
        CiPanelAssociationSource,
        verbose_name = 'CI-panel association source',
        on_delete = models.PROTECT,)

    clinical_indication = models.ForeignKey(
        ClinicalIndication,
        verbose_name = 'Clinical indication',
        on_delete = models.PROTECT,)

    panel = models.ForeignKey(
        Panel,
        verbose_name = 'Panel',
        on_delete = models.PROTECT,)

    current = models.BooleanField(verbose_name = 'Association is current')

    class Meta:
        db_table = 'clinical_indication_panel'

    def __str__(self):
        return str(self.id)


class ClinicalIndicationPanelUsage(models.Model):
    """ Defines the period of time in which the specified panel is/was
    associated with the specified clinical indication """

    clinical_indication_panel = models.ForeignKey(
        ClinicalIndicationPanel,
        verbose_name='Clinical indication',
        on_delete = models.PROTECT,)

    start_date = models.DateField(verbose_name = 'Start date')
    end_date = models.DateField(verbose_name = 'End date')

    class Meta:
        db_table = 'clinical_indication_panel_usage'

    def __str__(self):
        return str(self.id)


class Hgnc(models.Model):
    """ Defines a single HGNC ID (for a gene) """

    id = models.CharField(
        primary_key = True,
        unique = True,
        verbose_name = 'HGNC ID',
        max_length = 255)

    class Meta:
        db_table = 'hgnc'

    def __str__(self):
        return str(self.id)


class Gene(models.Model):
    """ Defines a single gene by its HGNC ID """

    hgnc = models.ForeignKey(
        Hgnc,
        verbose_name='HGNC ID',
        on_delete = models.PROTECT,)

    class Meta:
        db_table = 'gene'

    def __str__(self):
        return str(self.id)


class Confidence(models.Model):
    """ Defines the confidence level with which a gene or region is
    associated with a panel """

    confidence_level = models.CharField(
        verbose_name = 'Confidence level',
        unique = True,
        max_length = 255,)

    class Meta:
        db_table = 'confidence'

    def __str__(self):
        return str(self.id)


class Penetrance(models.Model):
    """ Defines the penetrance of the associated phenotype in the
    context of the associated clinical indication """

    penetrance = models.TextField(
        verbose_name = 'Penetrance',
        max_length = 255,
        unique = True,)

    class Meta:
        db_table = 'penetrance'

    def __str__(self):
        return str(self.id)


class ModeOfInheritance(models.Model):
    """ Defines the mode of inheritance of the associated phenotype in
    the context of the associated clinical indication """

    mode_of_inheritance = models.TextField(
        verbose_name = 'Mode of inheritance',
        max_length = 255,
        unique = True,)

    class Meta:
        db_table = 'mode_of_inheritance'
        verbose_name_plural = 'modes_of_inheritance'

    def __str__(self):
        return str(self.id)


class ModeOfPathogenicity(models.Model):
    """ Defines the mode of pathogenicity of the associated phenotype in
    the context of the associated clinical indication """

    mode_of_pathogenicity = models.TextField(
        verbose_name = 'Mode of pathogenicity',
        max_length = 255,
        unique = True,)

    class Meta:
        db_table = 'mode_of_pathogenicity'
        verbose_name_plural = 'modes_of_pathogenicity'

    def __str__(self):
        return str(self.id)


class PanelGene(models.Model):
    """ Defines a link between a single panel and a single gene """

    panel = models.ForeignKey(
        Panel,
        verbose_name = 'Panel ID',
        on_delete = models.PROTECT,)

    gene = models.ForeignKey(
        Gene,
        verbose_name = 'Gene ID',
        on_delete = models.PROTECT,)

    confidence = models.ForeignKey(
        Confidence,
        verbose_name = 'Confidence ID',
        on_delete = models.PROTECT,)

    moi = models.ForeignKey(
        ModeOfInheritance,
        verbose_name = 'Mode of inheritance ID',
        on_delete = models.PROTECT,)

    mop = models.ForeignKey(
        ModeOfPathogenicity,
        verbose_name = 'Mode of pathogenicity ID',
        on_delete = models.PROTECT,)

    penetrance = models.ForeignKey(
        Penetrance,
        verbose_name = 'Penetrance ID',
        on_delete = models.PROTECT,)

    justification = models.TextField(
        verbose_name = 'Justification',
        max_length = 255,)

    class Meta:
        db_table = 'panel_gene'

    def __str__(self):
        return str(self.id)


class Transcript(models.Model):
    """ Defines a single transcript by RefSeq ID """

    refseq_id = models.CharField(
        verbose_name = 'RefSeq ID',
        max_length = 255,
        unique = True,)

    class Meta:
        db_table = 'transcript'

    def __str__(self):
        return str(self.id)


class PanelGeneTranscript(models.Model):
    """ Defines a link between a single transcript and a single gene, in
    the context of a specific panel """

    panel_gene = models.ForeignKey(
        PanelGene,
        verbose_name = 'Panel/gene link ID',
        on_delete = models.PROTECT,)

    transcript = models.ForeignKey(
        Transcript,
        verbose_name = 'Transcript ID',
        on_delete = models.PROTECT,)

    justification = models.TextField(
        verbose_name = 'justification',
        max_length = 255,)

    class Meta:
        db_table = 'panel_gene_transcript'

    def __str__(self):
        return str(self.id)


class Haploinsufficiency(models.Model):
    """ Defines the haploinsufficiency score of the associated phenotype
    in the context of the associated clinical indication """

    haploinsufficiency = models.CharField(
        verbose_name = 'Haploinsufficiency score',
        unique = True,
        max_length = 255,)

    class Meta:
        db_table = 'haploinsufficiency'
        verbose_name_plural = 'haploinsufficiencies'

    def __str__(self):
        return str(self.id)


class Triplosensitivity(models.Model):
    """ Defines the triplosensitivity score of the associated phenotype
    in the context of the associated clinical indication """

    triplosensitivity = models.CharField(
        verbose_name = 'Triplosensitivity score',
        unique = True,
        max_length = 255,)

    class Meta:
        db_table = 'triplosensitivity'
        verbose_name_plural = 'triplosensitivities'

    def __str__(self):
        return str(self.id)


class RequiredOverlap(models.Model):
    """ GEL internal field relating to CNV detection method """

    required_overlap = models.CharField(
        verbose_name = 'Required percent overlap',
        unique = True,
        max_length = 255,)

    class Meta:
        db_table = 'required_overlap'

    def __str__(self):
        return str(self.id)


class VariantType(models.Model):
    """ Defines the type of variant  """

    variant_type = models.CharField(
        verbose_name = 'Variant type',
        max_length = 255,
        unique = True,)

    class Meta:
        db_table = 'variant_type'

    def __str__(self):
        return str(self.id)


class Region(models.Model):
    """ Defines a single region (CNV) """

    name = models.CharField(verbose_name = 'Region name', max_length = 255)
    chrom = models.CharField(verbose_name = 'Chromosome', max_length = 255)
    start = models.CharField(verbose_name = 'Region start', max_length = 255)
    end = models.CharField(verbose_name = 'Region end', max_length = 255)
    type = models.CharField(verbose_name = 'Region type', max_length = 255)

    class Meta:
        db_table = 'region'

    def __str__(self):
        return str(self.id)


class PanelRegion(models.Model):
    """ Defines a link between a single panel and a single region """

    panel = models.ForeignKey(
        Panel,
        verbose_name = 'Panel ID',
        on_delete = models.PROTECT,)

    confidence = models.ForeignKey(
        Confidence,
        verbose_name = 'Confidence level ID',
        on_delete = models.PROTECT,)

    moi = models.ForeignKey(
        ModeOfInheritance,
        verbose_name = 'Mode of inheritance ID',
        on_delete = models.PROTECT,)

    mop = models.ForeignKey(
        ModeOfPathogenicity,
        verbose_name = 'Mode of pathogenicity ID',
        on_delete = models.PROTECT,)

    penetrance = models.ForeignKey(
        Penetrance,
        verbose_name = 'Penetrance ID',
        on_delete = models.PROTECT,)

    region = models.ForeignKey(
        Region,
        verbose_name = 'Region ID',
        on_delete = models.PROTECT,)

    haplo = models.ForeignKey(
        Haploinsufficiency,
        verbose_name = 'Haploinsufficiency ID',
        on_delete = models.PROTECT,)

    triplo = models.ForeignKey(
        Triplosensitivity,
        verbose_name = 'Triplosensitivity ID',
        on_delete = models.PROTECT,)

    overlap = models.ForeignKey(
        RequiredOverlap,
        verbose_name = 'Required overlap ID',
        on_delete = models.PROTECT,)

    vartype = models.ForeignKey(
        VariantType,
        verbose_name = 'Variant type ID',
        on_delete = models.PROTECT,)

    justification = models.TextField(
        verbose_name = 'Justification',
        max_length = 255)

    class Meta:
        db_table = 'panel_region'

    def __str__(self):
        return str(self.id)


class RegionAnnotation(models.Model):
    """ Define an annotation for a region """

    region = models.ForeignKey(
        Region,
        verbose_name = 'Region ID',
        on_delete = models.PROTECT,)

    attribute = models.TextField(verbose_name = 'Attribute', max_length = 255)
    value = models.TextField(verbose_name = 'Value', max_length = 255)
    timestamp = models.DateTimeField(verbose_name = 'Timestamp')
    source = models.TextField(verbose_name = 'Source', max_length = 255)

    class Meta:
        db_table = 'region_annotation'

    def __str__(self):
        return str(self.id)
