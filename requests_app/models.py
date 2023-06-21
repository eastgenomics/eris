from django.db import models


class Panel(models.Model):
    """Defines a single internal panel"""

    # this is the PanelApp Panel id itself
    external_id = models.TextField(
        verbose_name="External Panel ID", max_length=255, null=True
    )

    panel_name = models.TextField(verbose_name="Panel Name", max_length=255)

    panel_source = models.TextField(
        verbose_name="Panel Source",
        max_length=255,
    )

    panel_version = models.CharField(
        verbose_name="Panel Version", max_length=255, null=True
    )

    grch37 = models.BooleanField(verbose_name="GRCh37")

    grch38 = models.BooleanField(verbose_name="GRCh38")

    test_directory = models.BooleanField(
        verbose_name="created by TD import",
        null=True,
        default=False,
    )

    created_date = models.DateField(
        verbose_name="created date", auto_now_add=True
    )

    created_time = models.TimeField(
        verbose_name="created time", auto_now_add=True
    )

    class Meta:
        db_table = "panel"

    def __str__(self):
        return str(self.id)


class ClinicalIndication(models.Model):
    """Defines a single clinical indication"""

    code = models.CharField(verbose_name="CI code", max_length=255)

    name = models.TextField(
        verbose_name="CI name",
        max_length=255,
    )

    gemini_name = models.TextField(
        verbose_name="Gemini name",
        max_length=255,
    )

    class Meta:
        db_table = "clinical_indication"

    def __str__(self):
        return str(self.id)


class ClinicalIndicationPanel(models.Model):
    """
    Defines an association between a clinical indication and a panel
    and when that association is made

    e.g. Normally when importing new Test Directory
    a new association between Clinical Indication and new version of
    Panel might be made
    """

    config_source = models.TextField(
        verbose_name="Config source",
        max_length=255,
    )

    td_version = models.CharField(
        verbose_name="TD version",
        max_length=255,
    )

    created_date = models.DateField(
        verbose_name="created date", auto_now_add=True
    )
    created_time = models.TimeField(
        verbose_name="created time", auto_now_add=True
    )
    last_updated = models.DateField(
        verbose_name="last updated", null=True, auto_now=True
    )

    clinical_indication = models.ForeignKey(
        ClinicalIndication,
        verbose_name="Clinical Indication id",
        on_delete=models.PROTECT,
    )

    panel = models.ForeignKey(
        Panel,
        verbose_name="Panel id",
        on_delete=models.PROTECT,
    )

    current = models.BooleanField(verbose_name="Latest association")

    class Meta:
        db_table = "clinical_indication_panel"

    def __str__(self):
        return str(self.id)


class ClinicalIndicationPanelHistory(models.Model):
    clinical_indication = models.ForeignKey(
        ClinicalIndication,
        verbose_name="Clinical Indication id",
        on_delete=models.PROTECT,
    )

    panel = models.ForeignKey(
        Panel,
        verbose_name="Panel id",
        on_delete=models.PROTECT,
    )

    created_date = models.DateField(
        verbose_name="created date", auto_now_add=True
    )
    created_time = models.TimeField(
        verbose_name="created time", auto_now_add=True
    )

    clinical_indication_panel = models.ForeignKey(
        ClinicalIndicationPanel,
        on_delete=models.PROTECT,
        verbose_name="Clinical Indication Panel id",
    )

    note = models.CharField(verbose_name="Note", max_length=255)

    class Meta:
        db_table = "clinical_indication_panel_history"

    def __str__(self):
        return str(self.id)


class Confidence(models.Model):
    """Defines the confidence level with which a gene or region is
    associated with a panel"""

    confidence_level = models.CharField(
        verbose_name="Confidence level", max_length=255, null=True
    )

    class Meta:
        db_table = "confidence"

    def __str__(self):
        return str(self.id)


class Penetrance(models.Model):
    """Defines the penetrance of the associated phenotype in the
    context of the associated clinical indication"""

    penetrance = models.CharField(
        verbose_name="Penetrance", max_length=255, null=True
    )

    class Meta:
        db_table = "penetrance"

    def __str__(self):
        return str(self.id)


class ModeOfInheritance(models.Model):
    """Defines the mode of inheritance of the associated phenotype in
    the context of the associated clinical indication"""

    mode_of_inheritance = models.CharField(
        verbose_name="Mode of inheritance", max_length=255, null=True
    )

    class Meta:
        db_table = "mode_of_inheritance"
        verbose_name_plural = "modes_of_inheritance"

    def __str__(self):
        return str(self.id)


class ModeOfPathogenicity(models.Model):
    """Defines the mode of pathogenicity of the associated phenotype in
    the context of the associated clinical indication"""

    mode_of_pathogenicity = models.CharField(
        verbose_name="Mode of pathogenicity", max_length=255, null=True
    )

    class Meta:
        db_table = "mode_of_pathogenicity"
        verbose_name_plural = "modes_of_pathogenicity"

    def __str__(self):
        return str(self.id)


class Gene(models.Model):
    """
    Defines a single gene by its HGNC ID

    :field: hgnc
    :field: gene_symbol
    :field: alias_symbol
    """

    hgnc_id = models.CharField(
        verbose_name="HGNC id", max_length=255, unique=True
    )

    gene_symbol = models.CharField(
        verbose_name="Gene Symbol", max_length=255, null=True
    )

    alias_symbols = models.CharField(
        verbose_name="Alias Symbols", max_length=255, null=True
    )

    previous_symbols = models.CharField(
        verbose_name="Previous Symbols", max_length=255, null=True
    )

    class Meta:
        db_table = "gene"

    def __str__(self):
        return str(self.id)


class Transcript(models.Model):
    """Defines a single transcript by RefSeq ID"""

    transcript = models.CharField(
        verbose_name="Transcript", max_length=255, null=True
    )

    source = models.CharField(
        verbose_name="MANE or HGMD", max_length=255, null=True, default=None
    )

    gene = models.ForeignKey(
        Gene, verbose_name="Gene id", on_delete=models.PROTECT
    )

    class Meta:
        db_table = "transcript"

    def __str__(self):
        return str(self.id)


class PanelGene(models.Model):
    """Defines a link between a single panel and a single gene"""

    panel = models.ForeignKey(
        Panel,
        verbose_name="Panel ID",
        on_delete=models.PROTECT,
    )

    gene = models.ForeignKey(
        Gene,
        verbose_name="Gene ID",
        on_delete=models.PROTECT,
    )

    confidence = models.ForeignKey(
        Confidence,
        verbose_name="Confidence ID",
        on_delete=models.PROTECT,
    )

    moi = models.ForeignKey(
        ModeOfInheritance,
        verbose_name="Mode of inheritance ID",
        on_delete=models.PROTECT,
    )

    mop = models.ForeignKey(
        ModeOfPathogenicity,
        verbose_name="Mode of pathogenicity ID",
        on_delete=models.PROTECT,
    )

    penetrance = models.ForeignKey(
        Penetrance,
        verbose_name="Penetrance ID",
        on_delete=models.PROTECT,
    )

    justification = models.TextField(
        verbose_name="Justification",
        max_length=255,
    )

    class Meta:
        db_table = "panel_gene"

    def __str__(self):
        return str(self.id)


class Haploinsufficiency(models.Model):
    """Defines the haploinsufficiency score of the associated phenotype
    in the context of the associated clinical indication"""

    haploinsufficiency = models.CharField(
        verbose_name="Haploinsufficiency score", max_length=255, null=True
    )

    class Meta:
        db_table = "haploinsufficiency"
        verbose_name_plural = "haploinsufficiencies"

    def __str__(self):
        return str(self.id)


class Triplosensitivity(models.Model):
    """Defines the triplosensitivity score of the associated phenotype
    in the context of the associated clinical indication"""

    triplosensitivity = models.CharField(
        verbose_name="Triplosensitivity score", max_length=255, null=True
    )

    class Meta:
        db_table = "triplosensitivity"
        verbose_name_plural = "triplosensitivities"

    def __str__(self):
        return str(self.id)


class RequiredOverlap(models.Model):
    """GEL internal field relating to CNV detection method"""

    required_overlap = models.CharField(
        verbose_name="Required percent overlap", max_length=255, null=True
    )

    class Meta:
        db_table = "required_overlap"

    def __str__(self):
        return str(self.id)


class VariantType(models.Model):
    """Defines the type of variant"""

    variant_type = models.CharField(
        verbose_name="Variant type", max_length=255, null=True
    )

    class Meta:
        db_table = "variant_type"

    def __str__(self):
        return str(self.id)


class Region(models.Model):
    """Defines a single region (CNV)"""

    name = models.CharField(verbose_name="Region name", max_length=255)
    chrom = models.CharField(verbose_name="Chromosome", max_length=255)
    start_37 = models.CharField(
        verbose_name="Region start grch37", max_length=255, null=True
    )
    end_37 = models.CharField(
        verbose_name="Region end grch37", max_length=255, null=True
    )
    start_38 = models.CharField(
        verbose_name="Region start grch38", max_length=255, null=True
    )
    end_38 = models.CharField(
        verbose_name="Region end grch38", max_length=255, null=True
    )
    type = models.CharField(verbose_name="Region type", max_length=255)

    panel = models.ForeignKey(
        Panel, verbose_name="panel id", on_delete=models.PROTECT
    )

    confidence = models.ForeignKey(
        Confidence,
        verbose_name="Confidence level ID",
        on_delete=models.PROTECT,
    )

    moi = models.ForeignKey(
        ModeOfInheritance,
        verbose_name="Mode of inheritance ID",
        on_delete=models.PROTECT,
    )

    mop = models.ForeignKey(
        ModeOfPathogenicity,
        verbose_name="Mode of pathogenicity ID",
        on_delete=models.PROTECT,
    )

    penetrance = models.ForeignKey(
        Penetrance,
        verbose_name="Penetrance ID",
        on_delete=models.PROTECT,
    )

    haplo = models.ForeignKey(
        Haploinsufficiency,
        verbose_name="Haploinsufficiency ID",
        on_delete=models.PROTECT,
    )

    triplo = models.ForeignKey(
        Triplosensitivity,
        verbose_name="Triplosensitivity ID",
        on_delete=models.PROTECT,
    )

    overlap = models.ForeignKey(
        RequiredOverlap,
        verbose_name="Required overlap ID",
        on_delete=models.PROTECT,
    )

    vartype = models.ForeignKey(
        VariantType,
        verbose_name="Variant type ID",
        on_delete=models.PROTECT,
    )

    justification = models.TextField(
        verbose_name="Justification", max_length=255
    )

    class Meta:
        db_table = "region"

    def __str__(self):
        return str(self.id)


class RegionAnnotation(models.Model):
    """Define an annotation for a region"""

    region = models.ForeignKey(
        Region,
        verbose_name="Region ID",
        on_delete=models.PROTECT,
    )

    attribute = models.TextField(verbose_name="Attribute", max_length=255)
    value = models.TextField(verbose_name="Value", max_length=255)
    timestamp = models.DateTimeField(verbose_name="Timestamp")
    source = models.TextField(verbose_name="Source", max_length=255)

    class Meta:
        db_table = "region_annotation"

    def __str__(self):
        return str(self.id)
