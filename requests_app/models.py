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
        max_length = 10)

    class Meta:
        db_table = 'reference_genome'
        verbose_name_plural = 'reference_genomes'
        indexes = [models.Index(fields=['reference_build'])]

    def __str__(self):
        return self.id


class Panel(models.Model):
    """ Defines a single internal panel """

    external_id = models.TextField(verbose_name='External panel ID')
    panel_source = models.TextField(verbose_name='Panel source')

    panel_version = models.CharField(
        verbose_name='Panel version',
        max_length = 10)

    reference_genome_id = models.ForeignKey(
        ReferenceGenome,
        verbose_name = 'Reference genome ID')

    class Meta:
        db_table = 'panel'
        verbose_name_plural = 'panels'
        indexes = [models.Index(fields=[
            'external_id',
            'panel_source',
            'panel_version',
            'reference_genome_id'])]

    def __str__(self):
        return self.id


class CiPanelAssociationSource(models.Model):
    """ Defines a source for the association between a specific clinical
    indication and a specific panel """

    source = models.TextField(verbose_name = 'Source name')
    date = models.DateField(verbose_name = 'Date')

    class Meta:
        db_table = 'ci_panel_association_source'
        verbose_name_plural = 'ci_panel_association_sources'
        indexes = [models.Index(fields=[
            'source',
            'date',])]

    def __str__(self):
        return self.id


class ClinicalIndication(models.Model):
    """ Defines a single clinical indication """

    code = models.CharField(verbose_name = 'CI code', max_length = 10)
    name = models.TextField(verbose_name = 'CI name')
    gemini_name = models.TextField(verbose_name = 'Gemini name')

    class Meta:
        db_table = 'clinical_indication'
        verbose_name_plural = 'clinical_indications'
        indexes = [models.Index(fields=[
            'code',
            'name',
            'gemini_name',])]

    def __str__(self):
        return self.id


class ClinicalIndicationPanel(models.Model):
    """ Defines an association between a clinical indication and a panel """

    source_id = models.ForeignKey(
        CiPanelAssociationSource,
        verbose_name = 'CI-panel association source')

    clinical_indication_id = models.ForeignKey(
        ClinicalIndication,
        verbose_name = 'Clinical indication')

    panel_id = models.ForeignKey(Panel, verbose_name = 'Panel')
    current = models.BooleanField(verbose_name = 'Association is current')

    class Meta:
        db_table = 'clinical_indication_panel'
        verbose_name_plural = 'clinical_indication_panels'
        indexes = [models.Index(fields=[
            'source_id',
            'clinical_indication_id',
            'panel_id',
            'current'])]

    def __str__(self):
        return self.id


class ClinicalIndicationPanelUsage(models.Model):
    """ Defines the period of time in which the specified panel is/was
    associated with the specified clinical indication """

    clinical_indication_panel_id = models.ForeignKey(
        ClinicalIndicationPanel,
        verbose_name='Clinical indication')

    start_date = models.DateField(verbose_name = 'Start date')
    end_date = models.DateField(verbose_name = 'End date')

    class Meta:
        db_table = 'clinical_indication_panel_usage'
        verbose_name_plural = 'clinical_indication_panel_usages'
        indexes = [models.Index(fields=[
            'clinical_indication_panel_id',
            'start_date',
            'end_date'])]

    def __str__(self):
        return self.id


class Hgnc(models.Model):
    """ Defines a single HGNC ID (for a gene) """

    id = models.IntegerField(primary_key = True)

    class Meta:
        db_table = 'hgnc'
        verbose_name_plural = 'hgncs'
        indexes = [models.Index(fields=['id'])]

    def __str__(self):
        return self.id


class Gene(models.Model):
    """ Defines a single gene by its HGNC ID """

    hgnc_id = models.ForeignKey(Hgnc, verbose_name='HGNC ID')

    class Meta:
        db_table = 'gene'
        verbose_name_plural = 'genes'
        indexes = [models.Index(fields=['hgnc_id'])]

    def __str__(self):
        return self.id


class Confidence(models.Model):
    """ Defines the confidence level with which a gene or region is
    associated with a panel """

    confidence_level = models.IntegerField(verbose_name = 'Confidence level')

    class Meta:
        db_table = 'confidence'
        verbose_name_plural = 'confidences'
        indexes = [models.Index(fields=['confidence_level'])]

    def __str__(self):
        return self.id


class Penetrance(models.Model):
    """ Defines the penetrance of the associated phenotype in the
    context of the associated clinical indication """

    penetrance = models.TextField(verbose_name = 'Penetrance')

    class Meta:
        db_table = 'penetrance'
        verbose_name_plural = 'penetrances'
        indexes = [models.Index(fields=['penetrance'])]

    def __str__(self):
        return self.id


class ModeOfInheritance(models.Model):
    """ Defines the mode of inheritance of the associated phenotype in
    the context of the associated clinical indication """

    mode_of_inheritance = models.TextField(
        verbose_name = 'Mode of inheritance')

    class Meta:
        db_table = 'mode_of_inheritance'
        verbose_name_plural = 'modes_of_inheritance'
        indexes = [models.Index(fields=['mode_of_inheritance'])]

    def __str__(self):
        return self.id


class ModeOfPathogenicity(models.Model):
    """ Defines the mode of pathogenicity of the associated phenotype in
    the context of the associated clinical indication """

    mode_of_pathogenicity = models.TextField(
        verbose_name = 'Mode of pathogenicity')

    class Meta:
        db_table = 'mode_of_pathogenicity'
        verbose_name_plural = 'modes_of_pathogenicity'
        indexes = [models.Index(fields=['mode_of_pathogenicity'])]

    def __str__(self):
        return self.id


class PanelGene(models.Model):
    """ Defines a link between a single panel and a single gene """

    panel_id = models.ForeignKey(Panel, verbose_name = 'Panel ID')
    gene_id = models.ForeignKey(Gene, verbose_name = 'Gene ID')

    confidence_id = models.ForeignKey(
        Confidence,
        verbose_name = 'Confidence ID')

    moi_id = models.ForeignKey(
        ModeOfInheritance,
        verbose_name = 'Mode of inheritance ID')

    mop_id = models.ForeignKey(
        ModeOfPathogenicity,
        verbose_name = 'Mode of pathogenicity ID')

    penetrance_id = models.ForeignKey(
        Penetrance,
        verbose_name = 'Penetrance ID')

    justification = models.TextField(verbose_name = 'Justification')

    class Meta:
        db_table = 'panel_gene'
        verbose_name_plural = 'panel_genes'
        indexes = [models.Index(fields=[
            'panel_id',
            'gene_id',
            'confidence_id',
            'moi_id',
            'mop_id',
            'penetrance_id',
            'justification'])]

    def __str__(self):
        return self.id


class Transcript(models.Model):
    """ Defines a single transcript by RefSeq ID """

    refseq_id = models.CharField(verbose_name = 'RefSeq ID', max_length = 20)

    class Meta:
        db_table = 'transcript'
        verbose_name_plural = 'transcripts'
        indexes = [models.Index(fields=['refseq_id'])]

    def __str__(self):
        return self.id


class PanelGeneTranscript(models.Model):
    """ Defines a link between a single transcript and a single gene, in
    the context of a specific panel """

    panel_gene_id = models.ForeignKey(
        PanelGene,
        verbose_name = 'Panel/gene link ID')

    transcript_id = models.ForeignKey(
        Transcript,
        verbose_name = 'Transcript ID')

    justification = models.TextField(verbose_name = 'justification')

    class Meta:
        db_table = 'panel_gene_transcript'
        verbose_name_plural = 'panel_gene_transcripts'
        indexes = [models.Index(fields=[
            'panel_gene_id',
            'transcript_id',
            'justification'])]

    def __str__(self):
        return self.id


class Haploinsufficiency(models.Model):
    """ Defines the haploinsufficiency score of the associated phenotype
    in the context of the associated clinical indication """

    haploinsufficiency = models.IntegerField(
        verbose_name = 'Haploinsufficiency score')

    class Meta:
        db_table = 'haploinsufficiency'
        verbose_name_plural = 'haploinsufficiencies'
        indexes = [models.Index(fields=['haploinsufficiency'])]

    def __str__(self):
        return self.id


class Triplosensitivity(models.Model):
    """ Defines the triplosensitivity score of the associated phenotype
    in the context of the associated clinical indication """

    triplosensitivity = models.IntegerField(
        verbose_name = 'Triplosensitivity score')

    class Meta:
        db_table = 'triplosensitivity'
        verbose_name_plural = 'triplosensitivities'
        indexes = [models.Index(fields=['triplosensitivity'])]

    def __str__(self):
        return self.id


class RequiredOverlap(models.Model):
    """ GEL internal field relating to CNV detection method """

    required_overlap = models.IntegerField(
        verbose_name = 'Required percent overlap')

    class Meta:
        db_table = 'required_overlap'
        verbose_name_plural = 'required_overlaps'
        indexes = [models.Index(fields=['required_overlap'])]

    def __str__(self):
        return self.id


class VariantType(models.Model):
    """ Defines the type of variant  """

    variant_type = models.CharField(
        verbose_name = 'Variant type', max_length = 10)

    class Meta:
        db_table = 'variant_type'
        verbose_name_plural = 'variant_types'
        indexes = [models.Index(fields=['variant_type'])]

    def __str__(self):
        return self.id


class Region(models.Model):
    """ Defines a single region (CNV) """

    name = models.CharField(verbose_name = 'Region name', max_length = 20)
    chrom = models.CharField(verbose_name = 'Chromosome', max_length = 5)
    start = models.IntegerField(verbose_name = 'Region start')
    end = models.IntegerField(verbose_name = 'Region end')

    class Meta:
        db_table = 'region'
        verbose_name_plural = 'regions'
        indexes = [models.Index(fields=['name', 'chrom', 'start', 'end'])]

    def __str__(self):
        return self.id


class PanelRegion(models.Model):
    """ Defines a link between a single panel and a single region """

    panel_id = models.ForeignKey(Panel, verbose_name = 'Panel ID')

    confidence_id = models.ForeignKey(
        Confidence,
        verbose_name = 'Confidence level ID')

    moi_id = models.ForeignKey(
        ModeOfInheritance,
        verbose_name = 'Mode of inheritance ID')

    mop_id = models.ForeignKey(
        ModeOfPathogenicity,
        verbose_name = 'Mode of pathogenicity ID')

    penetrance_id = models.ForeignKey(
        Penetrance,
        verbose_name = 'Penetrance ID')

    region_id = models.ForeignKey(Region, verbose_name = 'Region ID')

    haplo_id = models.ForeignKey(
        Haploinsufficiency,
        verbose_name = 'Haploinsufficiency ID')

    triplo_id = models.ForeignKey(
        Triplosensitivity,
        verbose_name = 'Triplosensitivity ID')

    overlap_id = models.ForeignKey(
        RequiredOverlap,
        verbose_name = 'Required overlap ID')

    vartype_id = models.ForeignKey(
        VariantType,
        verbose_name = 'Variant type ID')

    justification = models.TextField(verbose_name = 'Justification')

    class Meta:
        db_table = 'panel_region'
        verbose_name_plural = 'panel_regions'
        indexes = [models.Index(fields=[
            'panel_id',
            'confidence_id',
            'moi_id',
            'mop_id',
            'penetrance_id',
            'region_id',
            'haplo_id',
            'triplo_id',
            'overlap_id',
            'vartype_id',
            'justification'])]

    def __str__(self):
        return self.id


class RegionAnnotation(models.Model):
    """ Define an annotation for a region """

    region_id = models.ForeignKey(Region, verbose_name = 'Region ID')
    attribute = models.TextField(verbose_name = 'Attribute')
    value = models.TextField(verbose_name = 'Value')
    timestamp = models.DateTimeField(verbose_name = 'Timestamp')
    source = models.TextField(verbose_name = 'Source')

    class Meta:
        db_table = 'region_annotation'
        verbose_name_plural = 'region_annotations'
        indexes = [models.Index(fields=[
            'region_id',
            'attribute',
            'value',
            'timestamp',
            'source',
            ])]

    def __str__(self):
        return self.id
