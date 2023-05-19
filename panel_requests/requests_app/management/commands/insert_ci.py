#!usr/bin/env python

"""This script (called within seed.py) defines how cleaned data from
a test directory file is inserted into the database models.

Details of the required format for the test directory file can be found
in the README.
"""


# TODO: remove existing links between cis and panels if no longer supported
# TODO: deal with PA ids which aren't in the db (looking at you 489)


from datetime import datetime
from django.db import transaction
from packaging import version

from panel_requests.requests_app.models import (
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
)


def format_td_date(json_data: dict) -> datetime:
    """Retrieve and format the TD version date.

    args:
        json_data [dict]: all contents of TD

    returns:
        formatted_date [date]: as YYYY-MM-DD
    """

    formatted_date = datetime.strptime(json_data["date"], "%y%m%d")
    # datetime.strftime(formatted_date, "%Y-%m-%d")

    return formatted_date


def retrieve_panels_from_pa_id(ci_code, pa_id):
    """Given a PA id, retrieve any Panel records with that PA id and
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
        panel_source="panelapp", external_id=pa_id
    ).values()

    if len(matching_records) == 0:
        # if there aren't any, print a notification

        print(f"{ci_code}: No Panel record has panelapp ID {pa_id}")

    else:
        # otherwise, identify the most recent panel version

        max_v = str(
            max([version.parse(panel["panel_version"]) for panel in matching_records])
        )

        # restrict the queryset to records with that version

        panel_records = Panel.objects.filter(
            panel_source="panelapp", panel_version=max_v, external_id=pa_id
        )

    return panel_records


def retrieve_panels_from_hgncs(query_hgnc_list):
    """Given a list of HGNC ids, retrieve any non-PA Panel records with
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
        panel_source="panelapp",
        panelregion__isnull=False,
    )

    # if such panels exist, check their gene list

    if len(non_pa_records) > 0:
        matching_panels = []

        for panel in non_pa_records:
            # get a list of HGNC numbers for that Panel record

            hgnc_records = Hgnc.objects.filter(
                gene__panelgene__panel__id=panel.id
            ).values()

            panel_hgnc_list = [str(record["id"]) for record in hgnc_records]
            panel_hgnc_list.sort()

            # if this matches the supplied list, append the Panel record

            if panel_hgnc_list == query_hgnc_list:
                matching_panels.append(panel)

    if matching_panels:
        return matching_panels

    else:
        return None


def retrieve_unknown_metadata_records():
    """Return the records from the Confidence, ModeOfInheritance,
    ModeOfPathogenicity, Penetrance and Transcript models where value =
    'Not specified'.

    returns:
        conf [Confidence record]
        moi [ModeOfInheritance record]
        mop [ModeOfPathogenicity record]
        pen [Penetrance record]
        transcript [Transcript record]
    """

    conf, created = Confidence.objects.get_or_create(confidence_level="Not specified")

    moi, created = ModeOfInheritance.objects.get_or_create(
        mode_of_inheritance="Not specified"
    )

    mop, created = ModeOfPathogenicity.objects.get_or_create(
        mode_of_pathogenicity="Not specified"
    )

    pen, created = Penetrance.objects.get_or_create(penetrance="Not specified")

    transcript, created = Transcript.objects.get_or_create(refseq_id="Not specified")

    return conf, moi, mop, pen, transcript


def make_panels_from_hgncs(
    current: bool,
    source: CiPanelAssociationSource,
    td_date: datetime,
    ci: ClinicalIndication,
    hgnc_list: list,
):
    """Given a list of HGNC numbers, create a pair of new panels whose
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

    genome_37, created = ReferenceGenome.objects.get_or_create(reference_build="GRCh37")

    genome_38, created = ReferenceGenome.objects.get_or_create(reference_build="GRCh38")

    conf, moi, mop, pen, transcript = retrieve_unknown_metadata_records()

    # create two new Panel records with different ref genomes

    panel_37, created = Panel.objects.get_or_create(
        panel_source=source_str, external_id=ci_code_str, reference_genome=genome_37
    )

    panel_38, created = Panel.objects.get_or_create(
        panel_source=source_str, external_id=ci_code_str, reference_genome=genome_38
    )

    for panel_record in panel_37, panel_38:
        for hgnc_id in hgnc_list:
            # get/create Hgnc and Gene records

            hgnc_record, created = Hgnc.objects.get_or_create(id=hgnc_id)

            gene_record, created = Gene.objects.get_or_create(hgnc=hgnc_record)

            # create PanelGene record linking Panel to HGNC

            panel_gene, created = PanelGene.objects.get_or_create(
                panel=panel_record,
                gene=gene_record,
                justification=source_str,
                confidence=conf,
                moi=moi,
                mop=mop,
                penetrance=pen,
            )

            # link PanelGene record to 'Not specified' Transcript record

            panel_gene_transcript, created = PanelGeneTranscript.objects.get_or_create(
                panel_gene=panel_gene, transcript=transcript, justification=source_str
            )

        # link Panel record to CI via ClinicalIndicationPanel

        ci_panel, created = ClinicalIndicationPanel.objects.get_or_create(
            source=source, clinical_indication=ci, panel=panel_record, current=current
        )

        ci_panel_usage, created = ClinicalIndicationPanelUsage.objects.get_or_create(
            clinical_indication_panel=ci_panel, start_date=td_date, end_date=None
        )


@transaction.atomic
def insert_data(json_data: dict, td_current: bool) -> None:
    """This function insert TD data into DB

    e.g. command
    python manage.py seed test_dir <input_json> <Y/N>

    args:
        json_data [json dict]: data from TD
        td_current [bool]: is this the current TD version
    """

    print("Inserting test directory data into database...")

    # create a Source record for this td version

    td_date = format_td_date(json_data)

    source, created = CiPanelAssociationSource.objects.get_or_create(
        source=json_data["source"],
        date=td_date,
    )

    # create a ClinicalIndication record for each CI in the TD

    for indication in json_data["indications"]:
        ci, created = ClinicalIndication.objects.get_or_create(
            code=indication["code"],
            name=indication["name"],
            gemini_name=indication["gemini_name"],
        )

        # link each CI record to the appropriate Panel records

        hgnc_list = []

        if indication["panels"]:
            for element in indication["panels"]:
                # add any individual hgnc ids to a separate list

                if element and (element.upper().startswith("HGNC:")):
                    hgnc_list.append(element)

                # for PA panel ids, retrieve any matching Panel records

                elif element:
                    panel_records = retrieve_panels_from_pa_id(
                        indication["code"], element
                    )

                    # create ClinicalIndicationPanel links for those panels

                    if panel_records:
                        for panel in panel_records:
                            (
                                ci_panel,
                                created,
                            ) = ClinicalIndicationPanel.objects.get_or_create(
                                source=source,
                                clinical_indication=ci,
                                panel=panel,
                                current=td_current,
                            )

                            # TODO: need to edit previous ClinicalIndicationPanelUsage end_date

                            # if this link is new, also make a usage record

                            if created:
                                (
                                    _,
                                    created,
                                ) = ClinicalIndicationPanelUsage.objects.get_or_create(
                                    clinical_indication_panel=ci_panel,
                                    start_date=td_date,
                                    end_date=None,
                                )

        # if the CI has one or more associated HGNC ids:

        if hgnc_list:
            # check if any existing non-PA Panel records have the same genes

            matching_panels = retrieve_panels_from_hgncs(hgnc_list)

            # if they do, link them to the CI

            if matching_panels:
                for match in matching_panels:
                    ci_panel, created = ClinicalIndicationPanel.objects.get_or_create(
                        source=source,
                        clinical_indication=ci,
                        panel=match,
                        current=td_current,
                    )

                    # create a new usage record if one didn't already exist

                    if created:
                        (
                            ci_panel_usage,
                            created,
                        ) = ClinicalIndicationPanelUsage.objects.get_or_create(
                            clinical_indication_panel=ci_panel,
                            start_date=td_date,
                            end_date=None,
                        )

            # if not, make Panel records (2, bc genomes) and link to the CI

            else:
                make_panels_from_hgncs(td_current, source, td_date, ci, hgnc_list)

    print("Data insertion completed.")
