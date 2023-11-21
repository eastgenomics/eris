from django.db import models


class ReferenceGenome(models.Model):
    """Defines the reference genome builds"""

    reference_genome = models.CharField(
        verbose_name="reference genome build", max_length=255, null=False
    )

    class Meta:
        db_table = "reference_genome"

    def __str__(self):
        return str(self.id)


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

    # whether a panel is waiting for human review
    pending = models.BooleanField(
        verbose_name="pending activation",
        null=True,
        default=False,
    )

    class Meta:
        db_table = "panel"

    def __str__(self):
        return str(self.id)


class SuperPanel(models.Model):
    """
    Defines Superpanels - these are panels made of child panels added together.
    Otherwise very similar to Panels.
    """

    # this is the PanelApp Panel id itself
    external_id = models.CharField(
        verbose_name="external panel id", max_length=255, null=True
    )

    # metadata
    panel_name = models.CharField(verbose_name="Superpanel Name", max_length=255)

    panel_source = models.CharField(
        verbose_name="superpanel source",
        max_length=255,
    )

    panel_version = models.CharField(
        verbose_name="superpanel version",
        max_length=255,
        null=True,
    )

    # whether panel is created from test directory
    test_directory = models.BooleanField(
        verbose_name="created from test directory",
        null=True,
        default=False,
    )

    # whether panel is customized
    custom = models.BooleanField(
        verbose_name="custom superpanel",
        null=True,
        default=False,
    )

    # creation date
    created = models.DateTimeField(
        verbose_name="created",
        auto_now_add=True,
    )

    # whether a panel is waiting for human review
    pending = models.BooleanField(
        verbose_name="pending activation",
        null=True,
        default=False,
    )

    class Meta:
        db_table = "superpanel"

    def __str__(self):
        return str(self.id)


class PanelSuperPanel(models.Model):
    """
    Defines links between SuperPanels and their constituent Panels.
    Necessary because a SuperPanel can contain any number of panels,
    and a Panel could possibly be in multiple SuperPanels.
    """

    panel = models.ForeignKey(
        Panel, verbose_name="component panel", on_delete=models.PROTECT
    )

    superpanel = models.ForeignKey(
        SuperPanel, verbose_name="superpanel", on_delete=models.PROTECT
    )

    class Meta:
        db_table = "panel_superpanel"

    def __str__(self):
        return str(self.id)


class TestDirectoryRelease(models.Model):
    """
    Defines a test directory release.
    """

    release = models.CharField(
        verbose_name="test directory release", max_length=255, null=False
    )

    td_source = models.CharField(
        verbose_name="test directory source", max_length=255, null=False
    )

    config_source = models.CharField(
        verbose_name="config source", max_length=255, null=False
    )

    td_date = models.CharField(
        verbose_name="date from td file", max_length=255, null=False
    )

    class Meta:
        db_table = "td_release"

    def __str__(self):
        return str(self.id)


class TestDirectoryReleaseHistory(models.Model):
    """
    For adding information about when new tds were added, and by who
    """

    td_release = models.ForeignKey(
        TestDirectoryRelease,
        verbose_name="TD release",
        on_delete=models.PROTECT,
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
        db_table = "test_directory_release_history"

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


class ClinicalIndicationSuperPanel(models.Model):
    """
    Defines an association between a clinical indication and a superpanel
    and when that association is made

    e.g. Normally when importing new Test Directory
    a new association between Clinical Indication and new version of
    Panel might be made
    """

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
        verbose_name="clinical indication",
        on_delete=models.PROTECT,
    )  # required

    superpanel = models.ForeignKey(
        SuperPanel,
        verbose_name="superpanel",
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
        db_table = "clinical_indication_superpanel"

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


class ClinicalIndicationSuperPanelHistory(models.Model):
    # foreign key
    clinical_indication_superpanel = models.ForeignKey(
        ClinicalIndicationSuperPanel,
        on_delete=models.PROTECT,
        verbose_name="clinical indication superpanel id",
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
        db_table = "clinical_indication_superpanel_history"

    def __str__(self):
        return str(self.id)


class CiPanelTdRelease(models.Model):
    """
    Link a ClinicalIndication-Panel link, to those test directory releases
    which contain it. For example, clinical indication 'R001' might be linked to panel
    ID '5' in version 3 of the test directory, and also in version 4 of the test directory,
    making 2 entries in this CiPanelTdRelease table
    """

    ci_panel = models.ForeignKey(
        ClinicalIndicationPanel,
        verbose_name="Clinical Indication-Panel link",
        on_delete=models.PROTECT,
    )

    td_release = models.ForeignKey(
        TestDirectoryRelease,
        verbose_name="Test directory release",
        on_delete=models.PROTECT,
    )

    class Meta:
        db_table = "clinical_indication_panel_td_release"

    def __str__(self):
        return str(self.id)


class CiPanelTdReleaseHistory(models.Model):
    """
    Tracks the history of links made between a CiPanel
    and a Test Directory Release
    """

    cip_td = models.ForeignKey(
        CiPanelTdRelease,
        verbose_name="Clinical Indication Panel - Test Directory Release link",
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
        db_table = "ci_panel_td_history"

    def __str__(self):
        return str(self.id)


class CiSuperpanelTdRelease(models.Model):
    """
    Link a ClinicalIndication-Superpanel link, to those test directory releases
    which contain it. For example, clinical indication 'R009' might be linked to superpanel
    ID '10' in version 3 of the test directory, and also in version 4 of the test directory,
    making 2 entries in this CiSuperpanelTdRelease table
    """

    ci_superpanel = models.ForeignKey(
        ClinicalIndicationSuperPanel,
        verbose_name="Clinical Indication-SuperPanel link",
        on_delete=models.PROTECT,
    )

    td_release = models.ForeignKey(
        TestDirectoryRelease,
        verbose_name="Test directory release",
        on_delete=models.PROTECT,
    )

    class Meta:
        db_table = "clinical_indication_superpanel_td_release"

    def __str__(self):
        return str(self.id)


class CiSuperpanelTdReleaseHistory(models.Model):
    """
    Tracks the history of links made between a CiSuperpanel
    and a Test Directory Release
    """

    cip_td = models.ForeignKey(
        CiSuperpanelTdRelease,
        verbose_name="Clinical Indication SuperPanel - Test Directory Release link",
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
        db_table = "ci_superpanel_td_history"

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
        unique_together = ("hgnc_id", "gene_symbol", "alias_symbols")

    def __str__(self):
        return str(self.id)


class HgncRelease(models.Model):
    """
    Defines a particular release of HGNC, the source of gene IDs, symbols, and aliases
    """

    hgnc_release = models.CharField(
        verbose_name="Hgnc Release", max_length=255, unique=True
    )

    created = models.DateTimeField(
        verbose_name="created",
        help_text="date-time of release version's creation in Eris",
        auto_now_add=True,
    )

    class Meta:
        db_table = "hgnc_release"

    def __str__(self):
        return str(self.id)


class GeneHgncRelease(models.Model):
    """
    Links Genes to HGNC releases if:
    - the release is where the Gene was first assigned its Symbol
    - the Gene's Symbol changed in the release
    - the Gene's Alias changed in the release
    - the Gene was already in the database, and has not changed in a new release -
    this is to show that the Gene is still present in the newer release
    """

    gene = models.ForeignKey(
        Gene,
        verbose_name="Gene",
        on_delete=models.PROTECT,
        default=None,
    )

    hgnc_release = models.ForeignKey(
        HgncRelease,
        verbose_name="Hgnc Release",
        on_delete=models.PROTECT,
        default=None,
    )

    class Meta:
        db_table = "gene_hgncrelease"
        unique_together = ["gene", "hgnc_release"]

    def __str__(self):
        return str(self.id)


class GeneHgncReleaseHistory(models.Model):
    """
    Details changes to the links between Genes and particular HGNC releases, if:
    - the release is where the Gene was first assigned its Symbol
    - the Gene's Symbol changed in the release
    - The Gene's Alias changed in the release
    """

    gene_hgnc_release = models.ForeignKey(
        GeneHgncRelease,
        verbose_name="Gene-HGNC Release Link",
        on_delete=models.PROTECT,
        default=None,
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
        db_table = "gene_hgnc_release_history"

    def __str__(self):
        return str(self.id)


class TranscriptSource(models.Model):
    """
    Defines a particular source AND category of transcript information,
    e.g. MANE Select, MANE Plus Clinical, HGMD
    """

    source = models.CharField(
        verbose_name="Transcript Source",
        max_length=255,
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

    source = models.ForeignKey(
        TranscriptSource,
        verbose_name="Transcript source id",
        on_delete=models.PROTECT,
        default=None,
    )

    release = models.CharField(
        verbose_name="Transcript Release", max_length=255, null=True, default=None
    )

    created = models.DateTimeField(
        verbose_name="created",
        auto_now_add=True,
    )

    reference_genome = models.ForeignKey(
        ReferenceGenome, verbose_name="Reference genome", on_delete=models.PROTECT
    )

    class Meta:
        db_table = "transcript_release"
        # stop people reusing the same release version
        unique_together = ["source", "release", "reference_genome"]

    def __str__(self):
        return str(self.id)


class TranscriptFile(models.Model):
    """
    Files used to define a specific release of a transcript source -
    for example, MANE release 1.0
    """

    file_id = models.CharField(
        verbose_name="File ID in external storage (DNAnexus)",
        max_length=255,
        null=True,
        default=None,
    )

    file_type = models.CharField(
        verbose_name="File type", max_length=255, null=True, default=None
    )

    class Meta:
        db_table = "transcript_file"

    def __str__(self):
        return str(self.id)


class TranscriptReleaseTranscriptFile(models.Model):
    """Links transcript releases to the file(s) that characterise them"""

    transcript_release = models.ForeignKey(
        TranscriptRelease, verbose_name="Transcript release", on_delete=models.PROTECT
    )

    transcript_file = models.ForeignKey(
        TranscriptFile, verbose_name="Transcript file", on_delete=models.PROTECT
    )

    class Meta:
        db_table = "transcript_release_transcript_file"

    def __str__(self):
        return str(self.id)


class Transcript(models.Model):
    """Defines a single transcript by RefSeq ID"""

    transcript = models.CharField(verbose_name="Transcript", max_length=255, null=True)

    gene = models.ForeignKey(Gene, verbose_name="Gene id", on_delete=models.PROTECT)

    reference_genome = models.ForeignKey(
        ReferenceGenome, verbose_name="Reference genome", on_delete=models.PROTECT
    )

    class Meta:
        db_table = "transcript"
        unique_together = ["transcript", "gene", "reference_genome"]

    def __str__(self):
        return str(self.id)


class TranscriptReleaseTranscript(models.Model):
    """Defines the link between a single transcript and a single release"""

    transcript = models.ForeignKey(
        Transcript, verbose_name="Transcript", on_delete=models.CASCADE
    )

    release = models.ForeignKey(
        TranscriptRelease, verbose_name="Transcript release", on_delete=models.CASCADE
    )

    # match_version=True means the transcript WITH VERSION matches the
    # transcript in the release
    # if its False, that means only the base accession without version matches
    # None means it wasn't assessed
    match_version = models.BooleanField(
        verbose_name="Transcript matches version?",
        null=True,
        default=None,
    )

    match_base = models.BooleanField(
        verbose_name="Transcript matches accession base?",
        null=True,
        default=None,
    )

    default_clinical = models.BooleanField(
        verbose_name="Is the transcript clinical?",
        null=True,
        default=False,
    )

    # 'created' is here so that we can fetch the most up-to-date record,
    # if a transcript is looked up in a release more than once
    created = models.DateTimeField(
        verbose_name="created",
        auto_now_add=True,
    )

    class Meta:
        db_table = "transcript_release_link"

    def __str__(self):
        return str(self.id)


class GffRelease(models.Model):
    """
    Defines a particular release of the GFF file, the source of possibly-clinically relevant
    transcripts. Release versions must be unique for a given reference genome.
    """

    gff_release = models.CharField(
        verbose_name="Gff Release", max_length=255, unique=True
    )

    reference_genome = models.ForeignKey(
        ReferenceGenome,
        verbose_name="reference genome",
        on_delete=models.PROTECT,
    )

    created = models.DateTimeField(
        verbose_name="created",
        help_text="date-time of release version's creation in Eris",
        auto_now_add=True,
    )

    class Meta:
        db_table = "gff_release"
        unique_together = ["gff_release", "reference_genome"]

    def __str__(self):
        return str(self.id)


class TranscriptGffRelease(models.Model):
    """
    The link between a transcript and a GFF release.
    This indicates that the transcript is present in that GFF release.
    """

    transcript = models.ForeignKey(
        Transcript,
        verbose_name="Transcript",
        on_delete=models.PROTECT,
        default=None,
    )

    gff_release = models.ForeignKey(
        GffRelease,
        verbose_name="Gff File Release",
        on_delete=models.PROTECT,
        default=None,
    )

    class Meta:
        db_table = "transcript_gffrelease"
        unique_together = ["transcript", "gff_release"]

    def __str__(self):
        return str(self.id)


class TranscriptGffReleaseHistory(models.Model):
    """
    Tracking history for the link between a transcript and a GFF release.
    """

    transcript_gff = models.ForeignKey(
        TranscriptGffRelease,
        verbose_name="Transcript Gff",
        on_delete=models.PROTECT,
        default=None,
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
        db_table = "transcript_gff_file_history"

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
        null=True,
    )

    mop = models.ForeignKey(
        ModeOfPathogenicity,
        verbose_name="Mode of pathogenicity ID",
        on_delete=models.CASCADE,
        null=True,
    )

    penetrance = models.ForeignKey(
        Penetrance, verbose_name="Penetrance ID", on_delete=models.CASCADE, null=True
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

    # needed for backward deactivation because deletion of panel-gene link is probably not the best
    active = models.BooleanField(
        verbose_name="Active",
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


class Region(models.Model):  # TODO: work out how to split out by transcript
    """Defines a single region (CNV)"""

    name = models.CharField(verbose_name="Region name", max_length=255)
    verbose_name = models.CharField(verbose_name="Region verbose name", max_length=255)

    chrom = models.CharField(verbose_name="Chromosome", max_length=255)

    reference_genome = models.ForeignKey(
        ReferenceGenome,
        verbose_name="reference genome",
        on_delete=models.PROTECT,
    )

    start = models.CharField(verbose_name="Region start", max_length=255, null=True)

    end = models.CharField(verbose_name="Region end", max_length=255, null=True)

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
        null=True,
    )

    mop = models.ForeignKey(
        ModeOfPathogenicity,
        verbose_name="Mode of pathogenicity ID",
        on_delete=models.PROTECT,
        null=True,
    )

    penetrance = models.ForeignKey(
        Penetrance, verbose_name="Penetrance ID", on_delete=models.PROTECT, null=True
    )

    haplo = models.ForeignKey(
        Haploinsufficiency,
        verbose_name="Haploinsufficiency ID",
        on_delete=models.PROTECT,
        null=True,
    )

    triplo = models.ForeignKey(
        Triplosensitivity,
        verbose_name="Triplosensitivity ID",
        on_delete=models.PROTECT,
        null=True,
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
