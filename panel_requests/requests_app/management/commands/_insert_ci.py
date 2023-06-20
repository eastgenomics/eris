#!usr/bin/env python

# TODO: deal with PA ids which aren't in the db (looking at you 489) - Panel has been retired!

import os

from django.db import transaction

from panel_requests.requests_app.models import (
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


def _get_td_version(filename: str) -> str:
    """
    Get TD version from filename.

    :param: filename [str]: filename of TD json file

    returns:
        td_version [str]: TD version e.g. 4
    """
    td_filename, _ = os.path.splitext(filename)
    return td_filename.split("-")[-1].lstrip("v").strip()


def _retrieve_panel_from_pa_id(ci_code: str, pa_id: str) -> Panel:
    """
    Retrieve Panel record based on PA panel id.

    :param: ci_code [str]: clinical indication code
    :param: pa_id [str]: panelapp id
    """

    # retrieve Panel records directly created from PA panels with that external_id
    # there might be multiple Panel records with the same external_id
    # but different versions / ids
    panel_instance = (
        Panel.objects.filter(external_id=pa_id).order_by("-id").first()
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

    mop, _ = ModeOfPathogenicity.objects.get_or_create(
        mode_of_pathogenicity=None
    )

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

    # get current td version
    td_source = json_data["td_source"]
    td_version = _get_td_version(td_source)

    config_source = json_data["config_source"]
    td_date = json_data["date"]

    conf, moi, mop, pen = _retrieve_unknown_metadata_records()

    # check if previous CI-Panel record exists
    previous_ci_panels = ClinicalIndicationPanel.objects.filter(
        clinical_indication_id=ci.id
    ).order_by("-id")

    # there should only be one previous CI-Panel record for HGNC type panels
    previous_ci_panel = previous_ci_panels[0] if previous_ci_panels else None

    if previous_ci_panel:
        previous_ci_panel_version = _get_td_version(
            previous_ci_panel.td_version
        )

        # check if previous Panel record exists
        previous_panels = Panel.objects.filter(
            id=previous_ci_panel.panel_id, test_directory=True
        )
        # there should only be one Panel record associated for HGNC type panel
        previous_panel = previous_panels[0] if previous_panels else None

        # if there's a difference in panel name e.g. addition of HGNC
        if previous_panel:
            if float(td_version) > float(
                previous_ci_panel_version
            ) and previous_panel.panel_name != ",".join(
                hgnc_list
            ):  # TODO: same panel name should just update source rather than creating new panel
                print(
                    f"Deactivating previous CI-Panel record. CI-Panel id: {previous_ci_panel.id}"
                )

                # deactivate previous CI-Panel record
                previous_ci_panel.current = False
                previous_ci_panel.save()

                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=previous_ci_panel.id,
                    clinical_indication_id=previous_ci_panel.clinical_indication_id,
                    panel_id=previous_ci_panel.panel_id,
                    note=f"Deactivated by td source {td_source}",
                )

    unique_td_source = td_source + config_source + td_date
    # create Panel record
    panel_instance, _ = Panel.objects.update_or_create(
        panel_name=",".join(hgnc_list),
        external_id=None,
        panel_version=None,
        grch37=True,
        grch38=True,
        test_directory=True,
        defaults={
            "panel_source": unique_td_source,
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

    # link CI to Panel
    cpi_instance, created = ClinicalIndicationPanel.objects.get_or_create(
        td_version=td_source,
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

    td_source = json_data.get("td_source")
    td_version = _get_td_version(td_source)

    try:
        float(td_version)
    except ValueError:
        raise ValueError(f"Cannot parse TD version {td_version}")

    for indication in json_data["indications"]:
        skip_indication = False

        previous_cis = ClinicalIndication.objects.filter(
            code=indication["code"]
        ).order_by("-id")
        previous_ci = (
            previous_cis[0] if previous_cis else None
        )  # get the latest CI record

        # if there's a difference in name & gemini name, then create new CI record
        # and deactivate previous CI-Panels (if any)
        # since a new one will be created anyway
        if previous_ci:
            previous_ci_panels = ClinicalIndicationPanel.objects.filter(
                clinical_indication_id=previous_ci.id
            )

            if previous_ci_panels:
                # deactivate previous CI-Panel records
                for previous_ci_panel in previous_ci_panels:
                    previous_ci_panel_version = _get_td_version(
                        previous_ci_panel.td_version
                    )

                    # if current td version is greater than previous td version
                    # and the name and gemini name is different from previous ci
                    if float(td_version) > float(
                        previous_ci_panel_version
                    ) and (
                        previous_ci.name != indication["name"]
                        or previous_ci.gemini_name != indication["gemini_name"]
                    ):
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
                        # if the name and gemini name is the same & current td version is less than previous td version
                        # we don't do backward deactivation
                        skip_indication = True

        if (
            skip_indication
        ):  # skip this indication if it's not the latest version
            continue

        ci_instance, _ = ClinicalIndication.objects.get_or_create(
            code=indication["code"],
            name=indication["name"],
            gemini_name=indication["gemini_name"],
        )

        # link each CI record to the appropriate Panel records
        hgnc_list: list[str] = []

        if indication["panels"]:
            for pa_id in indication["panels"]:
                if not pa_id or not pa_id.strip():
                    continue

                # add any individual hgnc ids to a separate list
                if pa_id.upper().startswith("HGNC:"):
                    hgnc_list.append(pa_id.strip().upper())
                    continue

                # for PA panel ids, retrieve any matching Panel records
                panel_records = _retrieve_panel_from_pa_id(
                    indication["code"], pa_id
                )

                # create ClinicalIndicationPanel links for those panels

                if panel_records:
                    try:
                        # try to find CI-Panel record
                        cip_instance = ClinicalIndicationPanel.objects.get(
                            clinical_indication_id=ci_instance.id,
                            panel_id=panel_records.id,
                        )
                    except ClinicalIndicationPanel.DoesNotExist:
                        # create CI-Panel record if it doesn't exist
                        (
                            cip_instance,
                            created,
                        ) = ClinicalIndicationPanel.objects.get_or_create(
                            clinical_indication_id=ci_instance.id,
                            panel_id=panel_records.id,
                            td_version=json_data["td_source"],
                            config_source=json_data["config_source"],
                            current=True,
                        )

                    if created:
                        # if CI-Panel record is created, create a history record
                        ClinicalIndicationPanelHistory.objects.create(
                            clinical_indication_panel_id=cip_instance.id,
                            clinical_indication_id=ci_instance.id,
                            panel_id=panel_records.id,
                            note=f"Created by td source {td_source}",
                        )
                    else:
                        # if CI-Panel record already exists
                        # check if the td version or config source has changed
                        if (
                            cip_instance.td_version != json_data["td_source"]
                            or cip_instance.config_source
                            != json_data["config_source"]
                        ):
                            cip_instance.td_version = json_data["td_source"]
                            cip_instance.config_source = json_data[
                                "config_source"
                            ]
                            cip_instance.save()

                            ClinicalIndicationPanelHistory.objects.create(
                                clinical_indication_panel_id=cip_instance.id,
                                clinical_indication_id=ci_instance.id,
                                panel_id=panel_records.id,
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

    print("Data insertion completed.")
