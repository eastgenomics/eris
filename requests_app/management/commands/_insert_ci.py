#!usr/bin/env python

# TODO: deal with PA ids which aren't in the db (looking at you 489) - Panel has been retired!

import os

from django.db import transaction
from django.db.models import QuerySet

from ._utils import sortable_version, normalize_version

from requests_app.models import (
    Panel,
    ClinicalIndication,
    ClinicalIndicationPanel,
    Gene,
    Confidence,
    Penetrance,
    ModeOfInheritance,
    ModeOfPathogenicity,
    PanelGene,
    ClinicalIndicationPanelHistory,
)


def _get_td_version(filename: str) -> str | None:
    """
    Get TD version from filename.

    :param: filename [str]: filename of TD json file

    returns:
        td_version [str]: TD version e.g. 4
    """
    td_filename, _ = os.path.splitext(filename)

    try:
        return td_filename.split("-")[-1].lstrip("v").strip()
    except IndexError:
        print(f"TD version not found in filename {filename}")
        return None


def _retrieve_panel_from_pa_id(ci_code: str, pa_id: str) -> Panel | None:
    """
    Retrieve a single Panel record based on PA panel id.

    :param: ci_code [str]: clinical indication code
    :param: pa_id [str]: panelapp id
    """

    # retrieve Panel records directly created from PA panels with that external_id
    # there might be multiple Panel records with the same external_id
    # but different versions / ids thus we order by version
    panel_instance: Panel = (
        Panel.objects.filter(external_id=pa_id).order_by("-panel_version").first()
    )

    if not panel_instance:
        print(f"{ci_code}: No Panel record has panelapp ID {pa_id}")
        return None

    return panel_instance


def _retrieve_unknown_metadata_records():
    """
    Retrieve additional metadata records for PanelGene records

    returns:
        conf [Confidence record]
        moi [ModeOfInheritance record]
        mop [ModeOfPathogenicity record]
        pen [Penetrance record]
    """

    conf, _ = Confidence.objects.get_or_create(confidence_level=None)

    moi, _ = ModeOfInheritance.objects.get_or_create(mode_of_inheritance=None)

    mop, _ = ModeOfPathogenicity.objects.get_or_create(mode_of_pathogenicity=None)

    pen, _ = Penetrance.objects.get_or_create(penetrance=None)

    return conf, moi, mop, pen


def _make_panels_from_hgncs(
    json_data: dict,
    ci: ClinicalIndication,
    hgnc_list: list,
) -> None:
    """
    Make Panel records from a list of HGNC ids.

    args:
        current [bool]: is this the current TD version
        source [str]: source of data (variable from TD.json)
        ci [ClinicalIndication record]: the CI record to link to
        hgnc_list [list]: list of HGNC ids

    """

    skip_indication: bool = False

    # get current td version
    td_source: str = json_data["td_source"]
    td_version: str = _get_td_version(td_source)

    # TODO: what if TD version is lower

    config_source: str = json_data["config_source"]
    td_date: str = json_data["date"]

    unique_td_source: str = f"{td_source} + {config_source} + {td_date}"

    conf, moi, mop, pen = _retrieve_unknown_metadata_records()

    # create Panel record only when HGNC difference
    panel_instance, panel_created = Panel.objects.get_or_create(
        panel_name=",".join(hgnc_list),
        test_directory=True,
        defaults={
            "panel_source": unique_td_source,
            "grch37": True,
            "grch38": True,
            "external_id": None,
            "panel_version": None,
        },
    )

    # link each HGNC (gene) to the created Panel record
    for hgnc_id in hgnc_list:
        gene_instance, _ = Gene.objects.get_or_create(hgnc_id=hgnc_id)

        # create PanelGene record linking Panel to HGNC
        PanelGene.objects.get_or_create(
            panel_id=panel_instance.id,
            gene_id=gene_instance.id,
            justification=unique_td_source,
            confidence_id=conf.id,
            moi_id=moi.id,
            mop_id=mop.id,
            penetrance_id=pen.id,
        )

    # if new Panel record created
    # if previous CI-Panel record exist
    if panel_created:
        # if HGNC panel is of lower version
        # don't create new CI-Panel record

        # if HGNC panel is of higher version
        # create new CI-Panel record
        # deactivate old CI-Panel record

        # check if previous CI-Panel record exists
        previous_ci_panels: QuerySet[
            ClinicalIndicationPanel
        ] = ClinicalIndicationPanel.objects.filter(
            clinical_indication_id=ci.id,
            panel_id__test_directory=True,
            current=True,
        ).order_by(
            "-td_version"
        )
        # TODO: there is still some logic error here
        # deactivate all previous CI-Panel records
        # where Panel is created from Test Directory
        # ignore those from PanelApp
        for ci_panel in previous_ci_panels:
            # if previous CI-Panel record is made with
            # higher version of TD
            # we skip the whole CI-Panel creation for current CI
            if sortable_version(ci_panel.td_version) > sortable_version(td_version):
                skip_indication = True
                continue

            ci_panel.current = False
            ci_panel.save()

            ClinicalIndicationPanelHistory.objects.create(
                clinical_indication_panel_id=ci_panel.id,
                clinical_indication_id=ci_panel.clinical_indication_id,
                panel_id=ci_panel.panel_id,
                note=f"Deactivated by td source {td_source}",
            )

    if skip_indication:
        return

    # only chance we end up here is if previous CI-Panel record
    # exists and is of lower version
    # link CI to Panel
    cpi_instance, created = ClinicalIndicationPanel.objects.get_or_create(
        td_version=sortable_version(td_version),
        config_source=config_source,
        clinical_indication_id=ci.id,
        panel_id=panel_instance.id,
        current=True,
    )

    if created:
        ClinicalIndicationPanelHistory.objects.create(
            clinical_indication_panel_id=cpi_instance.id,
            clinical_indication_id=ci.id,
            panel_id=panel_instance.id,
            note=f"Created by td source {td_source}",
        )


@transaction.atomic
def insert_data(json_data: dict) -> None:
    """This function insert TD data into DB

    e.g. command
    python manage.py seed test_dir <input_json> <Y/N>

    args:
        json_data [json dict]: data from TD
        td_current [bool]: is this the current TD version
    """

    print("Inserting test directory data into database...")

    td_source: str = json_data.get("td_source")

    assert td_source, "Missing td_source in test directory json file"

    td_version: str = _get_td_version(td_source)

    assert td_version, f"Cannot parse TD version {td_version}"

    for indication in json_data["indications"]:
        skip_indication: bool = False

        r_code: str = indication["code"].strip()

        ci_instance, created = ClinicalIndication.objects.get_or_create(
            r_code=r_code,
            name=indication["name"],
            test_method=indication["test_method"],
        )

        if created:
            # scenario where CI change name but R code is the same
            # disable previous CI with wrong name
            previous_cis: list[ClinicalIndication] = ClinicalIndication.objects.filter(
                r_code=r_code
            ).exclude(
                name=indication["name"],
            )
            # !! there might be R104.3 and R104.4 which are active at the same time
            # thus both CI-Panel should be active

            if previous_cis:
                # deactivate previous CI-Panel records
                # because new one will be created

                # if just created CI, there shouldn't be any CI-Panel links
                for previous_instance in previous_cis:
                    previous_ci_panels: list[
                        ClinicalIndicationPanel
                    ] = ClinicalIndicationPanel.objects.filter(
                        clinical_indication_id=previous_instance.id,
                        current=True,  # get active CI-Panel records
                    ).order_by(
                        "-td_version"
                    )

                    if previous_ci_panels:
                        for previous_ci_panel in previous_ci_panels:
                            if sortable_version(
                                previous_ci_panel.td_version
                            ) > sortable_version(td_version):
                                # if the previous CI-Panel link is formed
                                # with a higher version TD
                                # skip the current CI-Panel record
                                skip_indication = True
                                break
                            else:
                                # deactivate previous CI-Panel records
                                # one CI could have multiple CI-Panel records
                                print(
                                    f"Deactivating previous CI-Panel record. CI-Panel id: {previous_ci_panel.id}"
                                )
                                previous_ci_panel.current = False
                                previous_ci_panel.save()

                                ClinicalIndicationPanelHistory.objects.create(
                                    clinical_indication_panel_id=previous_ci_panel.id,
                                    clinical_indication_id=previous_ci_panel.clinical_indication_id,
                                    panel_id=previous_ci_panel.panel_id,
                                    note=f"Deactivated by td source {td_source}",
                                )
                    else:
                        # there is no previous CI-Panel record
                        pass
            else:
                # there is no previous CI record
                pass
        else:
            # there might already be a previous CI record
            # and a TD with different config is seeded instead

            # is there possibility that a change in config
            # will change the CI-Panel links?

            # we get previous CI-Panel records and modify config source
            previous_ci_panels: QuerySet[
                ClinicalIndicationPanel
            ] = ClinicalIndicationPanel.objects.filter(
                clinical_indication_id=ci_instance.id,
                current=True,
                td_version__lte=sortable_version(td_version),
            )

            for cip_instance in previous_ci_panels:
                # we update existing CI-Panel record
                if cip_instance.config_source != json_data["config_source"]:
                    # take a note of the change
                    ClinicalIndicationPanelHistory.objects.create(
                        clinical_indication_panel_id=cip_instance.id,
                        clinical_indication_id=cip_instance.clinical_indication_id,
                        panel_id=cip_instance.panel_id,
                        note=f"Modified by td source {td_source}: {normalize_version(cip_instance.td_version)} -> {json_data['td_source']}, {cip_instance.config_source} -> {json_data['config_source']}",
                    )

                    cip_instance.config_source = json_data["config_source"]
                    cip_instance.save()

        if skip_indication:
            # here if there're previous CI-Panel record in DB
            # formed with TD version higher than current TD version
            continue

        # link each CI record to the appropriate Panel records
        hgnc_list: list[str] = []

        # attaching Panels to CI
        if indication["panels"]:
            for pa_id in indication["panels"]:
                if not pa_id or not pa_id.strip():
                    continue

                # add any individual hgnc ids to a separate list
                if pa_id.upper().startswith("HGNC:"):
                    hgnc_list.append(pa_id.strip().upper())
                    continue

                # for PA panel ids, retrieve latest version matching Panel records
                panel_record: Panel = _retrieve_panel_from_pa_id(
                    indication["code"],
                    pa_id,
                )

                # if we import the same version of TD but with different config source
                if panel_record:
                    (
                        cip_instance,
                        created,
                    ) = ClinicalIndicationPanel.objects.get_or_create(
                        clinical_indication_id=ci_instance.id,
                        panel_id=panel_record.id,
                        td_version=sortable_version(td_version),
                        config_source=json_data["config_source"],
                        current=True,
                    )

                    if created:
                        # if CI-Panel record is created, create a history record
                        ClinicalIndicationPanelHistory.objects.create(
                            clinical_indication_panel_id=cip_instance.id,
                            clinical_indication_id=ci_instance.id,
                            panel_id=panel_record.id,
                            note=f"Created by td source {td_source}",
                        )
                    else:
                        # only chance it gets here is if we are importing
                        # TD of the same version but with different config source
                        # td_source

                        # in that case we simply modify the existing CI-Panel record
                        if (
                            sortable_version(td_version)
                            >= sortable_version(cip_instance.td_version)
                            and cip_instance.config_source != json_data["config_source"]
                        ):
                            cip_instance.td_version = sortable_version(td_version)
                            cip_instance.config_source = json_data["config_source"]
                            cip_instance.save()

                            # take a note of the change
                            ClinicalIndicationPanelHistory.objects.create(
                                clinical_indication_panel_id=cip_instance.id,
                                clinical_indication_id=ci_instance.id,
                                panel_id=panel_record.id,
                                note=f"Modified by td source {td_source}: {cip_instance.td_version} -> {json_data['td_source']}, {cip_instance.config_source} -> {json_data['config_source']}",
                            )

                else:
                    # No panel record exist
                    # e.g. panel id 489 has been retired
                    print(
                        f"{indication['code']}: No Panel record has panelapp ID {pa_id}"
                    )
                    pass

        if hgnc_list:
            _make_panels_from_hgncs(json_data, ci_instance, hgnc_list)

        # deal with removing CI-Panel records which are no longer in TD
        # TODO: above

    print("Data insertion completed.")
