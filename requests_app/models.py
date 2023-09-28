from django.db import models

class Panel(models.Model):
    """Defines a single internal panel"""

    # this is the PanelApp Panel id itself
    external_id = models.CharField(
        verbose_name="external panel id", max_length=255, null=True
    )

    # metadata
    panel_name = models.CharField(verbose_name="Panel Name", max_length=255)

    panel_source = models.CharField(
        verbose_name="panel source",
        max_length=255,
    )

    panel_version = models.CharField(
        verbose_name="panel version",
        max_length=255,
        null=True,
    )

    # reference genome
    grch37 = models.BooleanField(verbose_name="grch37", default=True)
    grch38 = models.BooleanField(verbose_name="grch38", default=True)

    # whether panel is created from test directory
    test_directory = models.BooleanField(
        verbose_name="created from test directory",
        null=True,
        default=False,
    )

    # whether panel is customized
    custom = models.BooleanField(
        verbose_name="custom panel",
        null=True,
        default=False,
    )

    # creation date
    created = models.DateTimeField(
        verbose_name="created",
        auto_now_add=True,
    )

    pending = models.BooleanField(
        verbose_name="pending activation",
        null=True,
        default=False,
    )

    class Meta:
        db_table = "panel"

    def __str__(self):
        return str(self.id)


class ClinicalIndication(models.Model):
    """Defines a single clinical indication"""

    r_code = models.CharField(verbose_name="r code", max_length=255)

    name = models.TextField(
        verbose_name="clinical indication name",
        max_length=255,
    )

    test_method = models.CharField(
        verbose_name="test method",
        max_length=255,
    )

    pending = models.BooleanField(
        verbose_name="pending activation",
        null=True,
        default=False,
    )

    # creation date
    created = models.DateTimeField(
        verbose_name="created",
        auto_now_add=True,
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

    # metadata
    config_source = models.TextField(
        verbose_name="config source",
        max_length=255,
        null=True,
    )

    td_version = models.CharField(
        verbose_name="test directory version",
        max_length=255,
        null=True,
    )

    # creation date
    created = models.DateTimeField(
        verbose_name="created",
        auto_now_add=True,
    )

    last_updated = models.DateTimeField(
        verbose_name="last updated",
        null=True,
        auto_now=True,
    )

    # foreign keys
    clinical_indication = models.ForeignKey(
        ClinicalIndication,
        verbose_name="clinical indication id",
        on_delete=models.PROTECT,
    )  # required

    panel = models.ForeignKey(
        Panel,
        verbose_name="panel id",
        on_delete=models.PROTECT,
    )  # required

    # active status
    current = models.BooleanField(verbose_name="latest association")

    pending = models.BooleanField(
        verbose_name="pending review",
        null=True,
        default=False,
    )

    class Meta:
        db_table = "clinical_indication_panel"

    def __str__(self):
        return str(self.id)


class ClinicalIndicationPanelHistory(models.Model):
    # foreign key
    clinical_indication_panel = models.ForeignKey(
        ClinicalIndicationPanel,
        on_delete=models.PROTECT,
        verbose_name="clinical indication panel id",
    )

    # creation date
    created = models.DateTimeField(
        verbose_name="created",
        auto_now_add=True,
    )

    note = models.CharField(
        verbose_name="note",
        max_length=255,
    )

    user = models.CharField(
        verbose_name="user",
        max_length=255,
        null=True,
    )

    class Meta:
        db_table = "clinical_indication_panel_history"

    def __str__(self):
        return str(self.id)


class ClinicalIndicationTestMethodHistory(models.Model):
    clinical_indication = models.ForeignKey(
        ClinicalIndication,
        verbose_name="Clinical Indication id",
        on_delete=models.PROTECT,
    )
    created = models.DateTimeField(
        verbose_name="created",
        auto_now_add=True,
    )

    note = models.CharField(
        verbose_name="Note",
        max_length=255,
    )

    user = models.CharField(
        verbose_name="user",
        max_length=255,
        null=True,
    )

    class Meta:
        db_table = "clinical_indication_test_method_history"

    def __str__(self):
        return str(self.id)


class Confidence(models.Model):
    """Defines the confidence level with which a gene or region is
    associated with a panel"""

    confidence_level = models.CharField(
        verbose_name="Confidence level", max_length=20, null=True
    )

    class Meta:
        db_table = "confidence"

    def __str__(self):
        return str(self.id)


class Penetrance(models.Model):
    """Defines the penetrance of the associated phenotype in the
    context of the associated clinical indication"""

    penetrance = models.CharField(verbose_name="Penetrance", max_length=255, null=True)

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
    :field: alias_symbols
    """

    hgnc_id = models.CharField(verbose_name="HGNC id", max_length=20, unique=True)

    gene_symbol = models.CharField(
        verbose_name="Gene Symbol", max_length=255, null=True
    )

    alias_symbols = models.CharField(
        verbose_name="Alias Symbols", max_length=255, null=True
    )

    class Meta:
        db_table = "gene"

    def __str__(self):
        return str(self.id)


class TranscriptSource(models.Model):
    """
    Defines a particular source of transcript information, e.g. MANE
    """

    source = models.CharField(
        verbose_name="Transcript Source",
        max_length=255,
        null=True,
        default=None,
    )

    class Meta:
        db_table = "transcript_source"

    def __str__(self):
        return str(self.id)


class TranscriptRelease(models.Model):
    """
    Defines a specific release of a transcript source with metadata -
    for example, MANE release 1.0, or a specific HGMD dump
    """

    source = models.ForeignKey(TranscriptSource, verbose_name="Transcript source id", 
                               on_delete=models.PROTECT)
    
    external_release_version = models.CharField(
        verbose_name="Transcript Release",
        max_length=255,
        null=True,
        default=None
    )

    created = models.DateTimeField(
        verbose_name="created",
        auto_now_add=True,
    )
    
    file_id = models.CharField(
        verbose_name="File ID",
        max_length=255,
        null=True,
        default=None
    )

    external_db_dump_date = models.DateTimeField(
        verbose_name="External Db Dump Date"
    )

    class Meta:
        db_table = "transcript_release"

    def __str__(self):
        return str(self.id)


class TranscriptReleaseHistory(models.Model):
    transcript_release = models.ForeignKey(
        TranscriptRelease,
        verbose_name="TranscriptRelease id",
        on_delete=models.CASCADE,
    )

    created = models.DateTimeField(
        verbose_name="created",
        auto_now_add=True,
    )

    note = models.CharField(
        verbose_name="Note",
        max_length=255,
    )

    user = models.CharField(
        verbose_name="user",
        max_length=255,
        null=True,
    )

    class Meta:
        db_table = "transcript_release_history"

    def __str__(self):
        return str(self.id)


class Transcript(models.Model):
    """Defines a single transcript by RefSeq ID"""

    transcript = models.CharField(verbose_name="Transcript", max_length=255, null=True)

    gene = models.ForeignKey(Gene, verbose_name="Gene id", on_delete=models.PROTECT)

    reference_genome = models.CharField(
        verbose_name="Reference Genome",
        max_length=255,
        null=True,
        default=None,
    )

    transcript_release = models.ForeignKey(TranscriptRelease, 
                                           verbose_name="Transcript release id",
                                           on_delete=models.PROTECT)

    # release_match_type = is the transcript represented perfectly in the release
    # (e.g. both base and version match), or does just the base match?
    release_match_type = models.CharField(
        verbose_name="Transcript release match",
        max_length=255,
        null=True,
        default=None,
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
        on_delete=models.CASCADE,
    )

    gene = models.ForeignKey(
        Gene,
        verbose_name="Gene ID",
        on_delete=models.CASCADE,
    )

    confidence = models.ForeignKey(
        Confidence,
        verbose_name="Confidence ID",
        on_delete=models.CASCADE,
    )

    moi = models.ForeignKey(
        ModeOfInheritance,
        verbose_name="Mode of inheritance ID",
        on_delete=models.CASCADE,
    )

    mop = models.ForeignKey(
        ModeOfPathogenicity,
        verbose_name="Mode of pathogenicity ID",
        on_delete=models.CASCADE,
    )

    penetrance = models.ForeignKey(
        Penetrance,
        verbose_name="Penetrance ID",
        on_delete=models.CASCADE,
    )

    justification = models.TextField(
        verbose_name="Justification",
        max_length=255,
    )

    # needed for PanelGene backward deactivation purpose
    pending = models.BooleanField(
        verbose_name="Pending Review",
        default=False,
    )

    class Meta:
        db_table = "panel_gene"

    def __str__(self):
        return str(self.id)


class PanelGeneHistory(models.Model):
    panel_gene = models.ForeignKey(
        PanelGene,
        verbose_name="PanelGene id",
        on_delete=models.CASCADE,
    )

    created = models.DateTimeField(
        verbose_name="created",
        auto_now_add=True,
    )

    note = models.CharField(
        verbose_name="Note",
        max_length=255,
    )

    user = models.CharField(
        verbose_name="user",
        max_length=255,
        null=True,
    )

    class Meta:
        db_table = "panel_gene_history"

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
    verbose_name = models.CharField(verbose_name="Region verbose name", max_length=255)

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

    class Meta:
        db_table = "region"

    def __str__(self):
        return str(self.id)


class PanelRegion(models.Model):
    """Class to link Panel and Region"""

    region = models.ForeignKey(
        Region,
        verbose_name="Region ID",
        on_delete=models.PROTECT,
    )

    panel = models.ForeignKey(
        Panel,
        verbose_name="Panel ID",
        on_delete=models.PROTECT,
    )

    justification = models.TextField(
        verbose_name="Justification",
        max_length=255,
    )

    class Meta:
        db_table = "panel_region"

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


class PanelGeneTranscript(models.Model):
    """
    Defines which transcript is clinical for which gene
    for which Panel
    """

    panel = models.ForeignKey(
        Panel,
        verbose_name="Panel id",
        on_delete=models.PROTECT,
    )

    gene = models.ForeignKey(
        Gene,
        verbose_name="Gene id",
        on_delete=models.PROTECT,
    )

    transcript = models.ForeignKey(
        Transcript,
        verbose_name="Transcript id",
        on_delete=models.PROTECT,
    )

    class Meta:
        db_table = "panel_gene_transcript"

    def __str__(self):
        return str(self.id)
