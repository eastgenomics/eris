#!usr/bin/env python

"""This script (called within seed.py) defines how cleaned data from
a test directory file is inserted into the database models.

Abbreviations:
CI - clinical indication
DB - database
PA - PanelApp
TD - NHS England national genomic test directory
"""

""" TD data should be a json dict with the keys:

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


### STILL TO DO
# remove existing links between cis and panels if no longer supported
# collect hgnc ids into a separate panel
# deal with PA ids which aren't in the db (looking at you 489)


from datetime import datetime as dt
from django.db import transaction
from packaging import version

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


def format_td_date(json_data):
    """ Retrieve and format the TD version date.

    args:
        json_data [dict]: all contents of TD

    returns:
        formatted_date [date]: as YYYY-MM-DD
    """

    formatted_date = dt.strptime(json_data['date'], "%y%m%d")
    dt.strftime(formatted_date, "%Y-%m-%d")

    return formatted_date


def create_record_genomes():
    """ Get or create two ReferenceGenome records, one for each build.

    returns:
        genome_37 [Genome record]
        genome_38 [Genome record]
    """

    genome_37, created = ReferenceGenome.objects.get_or_create(
        reference_build = 'GRCh37')

    genome_38, created = ReferenceGenome.objects.get_or_create(
        reference_build = 'GRCh38')

    return genome_37, genome_38


def create_record_source(json_data):
    """ Get or create a CiPanelAssociationSource record which represents
    this TD version.

    args:
        json_data [dict]: all contents of TD

    returns:
        source [CiPanelAssociationSource record]
    """

    td_date = format_td_date(json_data)

    source, created = CiPanelAssociationSource.objects.get_or_create(
        source = json_data['source'],
        date = td_date,)

    return source, td_date


def create_record_ci(indication):
    """ Get or create a ClinicalIndication record.

    args:
        indication [dict]: TD data for one CI

    returns:
        ci [ClinicalIndication record]
    """

    ci, created = ClinicalIndication.objects.get_or_create(
            code = indication['code'],
            name = indication['name'],
            gemini_name = indication['gemini_name'],)

    return ci


def create_record_ci_panel(current, source, ci, panel):
    """ Get or create a ClinicalIndicationPanel record.

    args:
        current [bool]: whether this is the current td version
        source [CiPanelAssociationSource record]
        ci [ClinicalIndication record]
        panel [Panel record]

    returns:
        ci_panel [ClinicalIndicationPanel record]
        created [bool]: whether a new record was created
    """

    ci_panel, created = ClinicalIndicationPanel.objects.get_or_create(
        source = source,
        clinical_indication = ci,
        panel = panel,
        current = current)

    return ci_panel, created


def create_record_panel(genome, source, ci_code):
    """ Get or create a Panel record.

    args:
        genome [Genome record]
        source [str]
        ci_code [str]

    returns:
        panel_record [Panel record]
    """

    panel_record, created = Panel.objects.get_or_create(
        panel_source = source,
        external_id = ci_code,
        reference_genome = genome)

    return panel_record


def create_record_panel_gene(source, panel, gene, conf, moi, mop, pen):
    """ Get or create a PanelGene record.

    args:
        source [str]
        panel [Panel record]
        gene [Gene record]

    returns:
        panel_gene [PanelGene record]
    """

    panel_gene, created = PanelGene.objects.get_or_create(
        panel = panel,
        gene = gene,
        justification = source,
        confidence = conf,
        moi = moi,
        mop = mop,
        penetrance = pen)

    return panel_gene


def create_record_panel_gene_transcript(source, panel_gene, transcript):
    """ Get or create a PanelGeneTranscript record.

    args:
        source [str]
        panel_gene [PanelGene record]
        transcript [Transcript record]

    returns:
        panel_gene_transcript [PanelGeneTranscript record]
    """

    panel_gene_transcript, created = PanelGeneTranscript.objects.get_or_create(
        panel_gene = panel_gene,
        transcript = transcript,
        justification = source)

    return panel_gene_transcript


def create_record_usage(td_date, ci_panel):
    """ Get or create a ClinicalIndicationPanelUsage record.

    args:
        td_date [datetime]: date of TD version
        ci_panel [ClinicalIndicationPanel record]

    returns:
        ci_panel_usage [ClinicalIndicationPanelUsage record]
    """

    ci_panel_usage, created = ClinicalIndicationPanelUsage.objects.\
        get_or_create(
            clinical_indication_panel = ci_panel,
            start_date = td_date,
            end_date = None)

    return ci_panel_usage


def create_record_hgnc(hgnc_no):
    """ Get or create an Hgnc record.

    args:
        hgnc_no [str]: number only, not full HGNC id

    returns:
        hgnc_record [Hgnc record]
    """

    hgnc_record, created = Hgnc.objects.get_or_create(
        id = int(hgnc_no))

    return hgnc_record


def create_record_gene(hgnc_no):
    """ Get or create a Gene record.

    args:
        hgnc_no [int]: number only, not full HGNC id

    returns:
        gene_record [Gene record]
    """

    gene_record, created = Gene.objects.get_or_create(
        hgnc = hgnc_no)

    return gene_record


def retrieve_panels_from_pa_id(ci_code, pa_id):
    """ Given a PA id, retrieve any Panel records with that PA id and
    return the one with the highest PA version. If none exist, return
    None.

    If any such Panel records do exist, the number of them should be a
    multiple of 2, because there should be one for each reference
    genome.

    args:
        ci_code [str]: CI code associated with pa_id in the TD
        pa_id [str]: PA panel id

    returns:
        panel_records [Django queryset] or None
    """

    panel_records = None

    # retrieve Panel records directly created from PA panels with that id

    matching_records = Panel.objects.filter(
        panel_source = 'panelapp',
        external_id = pa_id).values()

    if len(matching_records) == 0:

        # if there aren't any, print a notification

        print('{}: No Panel record has panelapp ID {}'.format(ci_code, pa_id))

    else:

        # otherwise, identify the most recent panel version

        max_v = str(max([
            version.parse(panel['panel_version']) for panel in matching_records
            ]))

        # restrict the queryset to records with that version

        panel_records = Panel.objects.filter(
            panel_source = 'panelapp',
            panel_version = max_v,
            external_id = pa_id)

    return panel_records


def retrieve_panels_from_hgncs(query_hgnc_list):
    """ Given a list of HGNC ids, retrieve any non-PA Panel records with
    an identical gene list and with no associated regions. If none
    exist, return None.

    If any such Panel records do exist, the number of them should be a
    multiple of 2, because there should be one for each reference
    genome.

    PA records are excluded here because the metadata for their
    associated genes/regions is potentially not appropriate for a
    different CI.

    args:
        query_hgnc_list [list]: HGNC numbers (not full ids) as strs

    returns:
        matching_panels [list of Panel records] or None
    """

    query_hgnc_list.sort()

    # retrieve non-PA Panel records with no associated regions

    non_pa_records = Panel.objects.exclude(
        panel_source = 'panelapp',
        panelregion__isnull = False,
        )

    # if such panels exist, check their gene list

    if len(non_pa_records) > 0:

        matching_panels = []

        for panel in non_pa_records:

            # get a list of HGNC numbers for that Panel record

            hgnc_records = Hgnc.objects.filter(
                gene__panelgene__panel__id = panel.id).values()

            panel_hgnc_list = [str(record['id']) for record in hgnc_records]
            panel_hgnc_list.sort()

            # if this matches the supplied list, append the Panel record

            if panel_hgnc_list == query_hgnc_list:

                matching_panels.append(panel)

    if matching_panels:

        return matching_panels

    else:

        return None


def retrieve_unknown_metadata_records():
    """ Return the records from the Confidence, ModeOfInheritance,
    ModeOfPathogenicity, Penetrance and Transcript models where value =
    'Not specified'.

    returns:
        conf [Confidence record]
        moi [ModeOfInheritance record]
        mop [ModeOfPathogenicity record]
        pen [Penetrance record]
        transcript [Transcript record]
    """

    conf, created = Confidence.objects.get_or_create(
        confidence_level = 'Not specified')

    moi, created = ModeOfInheritance.objects.get_or_create(
        mode_of_inheritance = 'Not specified')

    mop, created = ModeOfPathogenicity.objects.get_or_create(
        mode_of_pathogenicity = 'Not specified')

    pen, created = Penetrance.objects.get_or_create(
        penetrance = 'Not specified')

    transcript, created = Transcript.objects.get_or_create(
        refseq_id = 'Not specified')

    return conf, moi, mop, pen, transcript


def make_panels_from_hgncs(current, source, ci, hgnc_list):
    """ Given a list of HGNC numbers, create a pair of new panels whose
    genes are those associated with those IDs.

    Two panels are required because of the two reference genome builds.

    args:
        current [bool]
        source [CiPanelAssociationSource record]
        ci [ClinicalIndication record]
        hgnc_list [list]: list of HGNC numbers (not full ids) as strs
    """

    source_str = str(source.source)
    ci_code_str = str(ci.code)

    # make sure ReferenceGenome and metadata records exist

    genome_37, genome_38 = create_record_genomes()

    conf, moi, mop, pen, transcript = retrieve_unknown_metadata_records()

    # create two new Panel records with different ref genomes

    panel_37 = create_record_panel(genome_37, source_str, ci_code_str)
    panel_38 = create_record_panel(genome_38, source_str, ci_code_str)


    for panel_record in panel_37, panel_38:
        for hgnc_no in hgnc_list:

            # get/create Hgnc and Gene records

            hgnc_record = create_record_hgnc(hgnc_no)
            gene = create_record_gene(hgnc_record)

            # create PanelGene record linking Panel to HGNC

            panel_gene = create_record_panel_gene(
                source_str,
                panel_record,
                gene,
                conf,
                moi,
                mop,
                pen)

            # link PanelGene record to 'Not specified' Transcript record

            panel_gene_transcript = create_record_panel_gene_transcript(
                source_str,
                panel_gene,
                transcript)

        # link Panel record to CI via ClinicalIndicationPanel

        panel_ci = create_record_ci_panel(current, source, ci, panel_record)



@transaction.atomic
def insert_data(json_data, td_current):
    """ Insert TD data into the DB.

    args:
        json_data [json dict]: data from TD
        td_current [bool]: is this the current TD version
    """

    print('Inserting test directory data into the database...')

    # create a Source record for this td version

    source, td_date = create_record_source(json_data)

    # create a ClinicalIndication record for each CI in the TD

    for indication in json_data['indications']:

        ci = create_record_ci(indication)

        # link each CI record to the appropriate Panel records

        hgnc_list = []

        if indication['panels']:
            for element in indication['panels']:

                # add any individual hgnc ids to a separate list

                if element and (element.upper().startswith("HGNC:")):
                    hgnc_list.append(element[5:])

                # for PA panel ids, retrieve any matching Panel records

                elif element:

                    panel_records = retrieve_panels_from_pa_id(
                        indication['code'],
                        element)

                    # create ClinicalIndicationPanel links for those panels

                    if panel_records:
                        for panel in panel_records:

                            ci_panel, created = create_record_ci_panel(
                                td_current,
                                source,
                                ci,
                                panel)

                            # if this link is new, also make a usage record

                            if created:

                                ci_panel_usage = create_record_usage(
                                    td_date,
                                    ci_panel)

        # if the CI has one or more associated HGNC ids:

        if hgnc_list:

            # check if any existing non-PA Panel records have the same genes

            matching_panels = retrieve_panels_from_hgncs(hgnc_list)

            # if they do, link them to the CI

            if matching_panels:
                for match in matching_panels:

                    ci_panel, created = create_record_ci_panel(
                        td_current,
                        source,
                        ci,
                        match)

            # if not, make Panel records (2, bc genomes) and link to the CI

            else:

                make_panels_from_hgncs(td_current, source, ci, hgnc_list)

    print('Data insertion completed.')
