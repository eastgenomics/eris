
""" Defines how cleaned data from either panelapp or a request form,
representing a single panel, is inserted into the database models.
Called within seed.py.
"""

""" Panel data passed to this script (generated by either parse_pa or
parse_form) should be a dict with the keys:

{
'panel_source',
'external_id',
'panel_version',
'genes' : [
    'transcript',
    'hgnc_id',
    'confidence_level',
    'mode_of_inheritance',
    'mode_of_pathogenicity',
    'penetrance',
    'gene_justification',
    'transcript_justification',
    ],
'regions' : [
    'confidence_level',
    'mode_of_inheritance',
    'mode_of_pathogenicity',
    'penetrance',
    'name',
    'chrom',
    'start_37',
    'end_37',
    'start_38',
    'end_38',
    'type',
    'haploinsufficiency',
    'triplosensitivity',
    'required_overlap',
    'variant_type',
    'justification',
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

    # define the two reference genomes

    ref_genome_37, created = ReferenceGenome.objects.get_or_create(
        reference_build = 'GRCh37')

    ref_genome_38, created = ReferenceGenome.objects.get_or_create(
        reference_build = 'GRCh38')

    # create two new panels (one for each genome build)

    panel_37, created = Panel.objects.get_or_create(
        external_id = parsed_data['external_id'],
        panel_name = parsed_data['panel_name'],
        panel_source = parsed_data['panel_source'],
        panel_version = parsed_data['panel_version'],
        reference_genome_id = ref_genome_37.id,)

    panel_38, created = Panel.objects.get_or_create(
        external_id = parsed_data['external_id'],
        panel_name = parsed_data['panel_name'],
        panel_source = parsed_data['panel_source'],
        panel_version = parsed_data['panel_version'],
        reference_genome_id = ref_genome_38.id,)

    # for each panel gene, populate the gene attribute models

    for single_gene in parsed_data['genes']:

        hgnc, created = Hgnc.objects.get_or_create(
            id = single_gene['hgnc_id'],)

        gene, created = Gene.objects.get_or_create(
            hgnc_id = hgnc.id,)

        confidence, created = Confidence.objects.get_or_create(
            confidence_level = single_gene['confidence_level'],)

        moi, created = ModeOfInheritance.objects.get_or_create(
            mode_of_inheritance = single_gene['mode_of_inheritance'],)

        # value for 'mode_of_pathogenicity' might be empty
        if single_gene['mode_of_pathogenicity']:
            mop, created = ModeOfPathogenicity.objects.get_or_create(
                mode_of_pathogenicity = single_gene[
                    'mode_of_pathogenicity'],)

        else:
            mop, created = ModeOfPathogenicity.objects.get_or_create(
                mode_of_pathogenicity = 'None',)

        # value for 'penetrance' might be empty
        if single_gene['penetrance']:
            penetrance, created = Penetrance.objects.get_or_create(
                penetrance = single_gene['penetrance'],)

        else:
            penetrance, created = Penetrance.objects.get_or_create(
                penetrance = 'None',)

        # value for 'transcript' might be empty
        if single_gene['transcript']:
            transcript, created = Transcript.objects.get_or_create(
                refseq_id = single_gene['transcript'],)

        else:
            transcript, created = Transcript.objects.get_or_create(
                refseq_id = 'None',)

        # link the gene to both panel instances (37 and 38)

        for panel_instance in panel_37, panel_38:

            panel_gene, created = PanelGene.objects.get_or_create(
                panel_id = panel_instance.id,
                gene_id = gene.id,
                confidence_id = confidence.id,
                moi_id = moi.id,
                mop_id = mop.id,
                penetrance_id = penetrance.id,
                justification = single_gene['gene_justification'],)

            # link each PanelGene instance to the appropriate transcript

            panel_gene_transcript, created = PanelGeneTranscript.objects\
                .get_or_create(
                    panel_gene_id = panel_gene.id,
                    transcript_id = transcript.id,
                    justification = single_gene[
                        'transcript_justification'])

    # for each panel region, populate the region attribute models

    for single_region in parsed_data['regions']:

        confidence, created = Confidence.objects.get_or_create(
            confidence_level = single_region['confidence_level'],)

        moi, created = ModeOfInheritance.objects.get_or_create(
            mode_of_inheritance = single_region['mode_of_inheritance'],)

        # value for 'mode_of_pathogenicity' might be empty
        if single_region['mode_of_pathogenicity']:
            mop, created = ModeOfPathogenicity.objects.get_or_create(
                mode_of_pathogenicity = single_region[
                    'mode_of_pathogenicity'])

        else:
            mop, created = ModeOfPathogenicity.objects.get_or_create(
                mode_of_pathogenicity = 'None')

        # value for 'penetrance' might be empty
        if single_region['penetrance']:
            penetrance, created = Penetrance.objects.get_or_create(
                penetrance = single_region['penetrance'],)

        else:
            penetrance, created = Penetrance.objects.get_or_create(
                penetrance = 'None',)

        vartype, created = VariantType.objects.get_or_create(
            variant_type = single_region['variant_type'],)

        overlap, created = RequiredOverlap.objects.get_or_create(
            required_overlap = single_region['required_overlap'],)

        # value for 'haploinsufficiency' might be empty
        if single_region['haploinsufficiency']:
            haplo, created = Haploinsufficiency.objects.get_or_create(
                haploinsufficiency = single_region['haploinsufficiency'],)

        else:
            haplo, created = Haploinsufficiency.objects.get_or_create(
                haploinsufficiency = 'None',)

        # value for 'triplosensitivity' might be empty
        if single_region['triplosensitivity']:
            triplo, created = Triplosensitivity.objects.get_or_create(
                triplosensitivity = single_region['triplosensitivity'],)

        else:
            triplo, created = Triplosensitivity.objects.get_or_create(
                triplosensitivity = 'None',)

        # create the two genome build-specific regions

        for panel_instance in panel_37, panel_38:

            if panel_instance == panel_37:

                region, created = Region.objects.get_or_create(
                    name = single_region['name'],
                    chrom = single_region['chrom'],
                    start = single_region['start_37'],
                    end = single_region['end_37'],
                    type = single_region['type'],)

            elif panel_instance == panel_38:

                region, created = Region.objects.get_or_create(
                    name = single_region['name'],
                    chrom = single_region['chrom'],
                    start = single_region['start_38'],
                    end = single_region['end_38'],
                    type = single_region['type'],)

            # link each region to the appropriate panel

            panel_region, created = PanelRegion.objects.get_or_create(
                panel_id = panel_instance.id,
                confidence_id = confidence.id,
                moi_id = moi.id,
                mop_id = mop.id,
                penetrance_id = penetrance.id,
                region_id = region.id,
                haplo_id = haplo.id,
                triplo_id = triplo.id,
                overlap_id = overlap.id,
                vartype_id = vartype.id,
                justification = single_region['justification'],)
