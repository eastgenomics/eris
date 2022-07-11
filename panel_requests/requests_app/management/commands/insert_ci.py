#!usr/bin/env python

"""This script (called within seed.py) defines how cleaned data from
a test directory file is inserted into the database models.
"""

""" Test directory data should be a dict with the keys:

{
source,
date,
indications : [
	{
	code,
	name,
	gemini_name,
	panels : [id_1, id_2, ... , id_N],
	}
	{ci_2},
	...
	{ci_N},
	],
}
"""


from django.db import transaction

from requests_app.models import (
    ReferenceGenome,
    Panel,
    CiPanelAssociationSource,
    ClinicalIndication,
    ClinicalIndicationPanel,
    ClinicalIndicationPanelUsage,
    Hgnc,
    Gene,
    Confidence,
    Penetrance,
    ModeOfInheritance,
    ModeOfPathogenicity,
    PanelGene,
    Transcript,
    PanelGeneTranscript,
    Haploinsufficiency,
    Triplosensitivity,
    RequiredOverlap,
    VariantType,
    Region,
    PanelRegion,
    RegionAnnotation)


@transaction.atomic
def insert_data(parsed_data):

    ## define the two reference genomes

    ref_genome_37, created = ReferenceGenome.objects.get_or_create(
        reference_build = 'GRCh37')

    ref_genome_38, created = ReferenceGenome.objects.get_or_create(
        reference_build = 'GRCh38')

    # define the test directory as the source

    source, created = CiPanelAssociationSource.objects.get_or_create(
        source = parsed_data['source'],
        date = parsed_data['date'],)

    # create each clinical indication

    for indication in parsed_data['indications']:

        ci, created = ClinicalIndication.objects.get_or_create(
            code = indication['code'],
            name = indication['name'],
            gemini_name = indication['gemini_name'],)

        # link each CI to its associated panels

        for panel in indication['panels']:

            ci_panel, created = ClinicalIndicationPanel.objects\
                .get_or_create(
                    source_id = source.id,
                    clinical_indication_id = ci.id,
                    panel_id = panel.id,
                    current = True,)

            ci_panel_usage, created = ClinicalIndicationPanelUsage.objects\
                .get_or_create(
                    clinical_indication_panel_id = ci_panel.id,
                    start_date = parsed_data['date'],
                    end_date = None,)
