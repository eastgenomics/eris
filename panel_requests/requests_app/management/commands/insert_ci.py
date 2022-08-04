#!usr/bin/env python

"""This script (called within seed.py) defines how cleaned data from
a test directory file is inserted into the database models.
"""

""" Test directory data should be a json dict with the keys:

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
# deal with panelapp ids which aren't in the db (looking at you 489)


from datetime import datetime as dt
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
def insert_data(json_data, td_current):

    if td_current == 'Y':
        current_td = True

    elif td_current == 'N':
        current_td = False

    # define the test directory as the source

    date_object = dt.strptime(json_data['date'], "%y%m%d")
    dt.strftime(date_object, "%Y-%m-%d")

    source, created = CiPanelAssociationSource.objects.get_or_create(
        source = json_data['source'],
        date = date_object,)

    # create each clinical indication

    for indication in json_data['indications']:

        ci, created = ClinicalIndication.objects.get_or_create(
            code = indication['code'],
            name = indication['name'],
            gemini_name = indication['gemini_name'],)

        # link each ci to its panels as specified in the td (if any)

        hgnc_list = []

        if indication['panels']:
            for element in indication['panels']:

                # add any individual hgnc ids to a separate list

                if element and (element.upper().startswith("HGNC:")):
                    hgnc_list.append(element[5:])

                # for panelapp panel ids, retrieve panel objects and link to ci

                elif element:

                    # get all panel records with that panelapp id
                    # there should be either 0 or a multiple of 2 (bc genomes)

                    panel_records = Panel.objects.filter(
                        panel_source = 'panelapp',
                        external_id = element).values()

                    # print a notification if there are no records

                    if len(panel_records) == 0:

                        print('No record has panelapp ID {}'.format(element))

                    # if there are records:

                    else:

                        # identify the most recent panel version

                        max_v = '0'

                        for record in panel_records:
                            if float(record['panel_version']) > float(max_v):

                                max_v = record['panel_version']

                        # restrict queryset to records with that version

                        most_recent = panel_records.filter(
                            panel_version = max_v).values()

                        # link these records to the ci

                        for record in most_recent:

                            ci_panel, created = ClinicalIndicationPanel.\
                                objects.get_or_create(
                                    source_id = source.id,
                                    clinical_indication_id = ci.id,
                                    panel_id = record['id'],
                                    current = current_td)

                            # if this link is new, also make a usage record

                            if created:

                                (ci_panel_usage,
                                created) = ClinicalIndicationPanelUsage.\
                                objects.get_or_create(
                                    clinical_indication_panel_id = ci_panel.id,
                                    start_date = date_object,
                                    end_date = None)

                                # do we need to do different things here
                                # depending on whether the td version is the
                                # current one or not? more things to consider

        # deal with the list of hgnc ids
        # does a panel of those genes already exist?
        # if not, make a panel (issue with metadata :/ )
        # either way, link it to the ci
