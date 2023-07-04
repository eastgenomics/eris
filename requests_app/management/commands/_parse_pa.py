#!usr/bin/env python

# TODO:PanelApp doesn't have grch37 coordinates for all regions


from panelapp.Panelapp import Panel
from panelapp import queries


def _clean_val(val: str):
    """
    Deal with empty strings and lists.

    args:
        val [str]: value to be cleaned

    """
    if isinstance(val, str):
        return val.strip() if val.strip() else None
    elif isinstance(val, list):
        return ",".join([v for v in val]) if val else None
    else:
        return val


def _add_gene_info(panel: Panel, info_dict: dict) -> dict:
    """
    Iterate over every gene in the panel and retrieve the data
    Add data to info_dict

    args:
        panel [Panel]: PanelApp data for one panel
        info_dict [dict]: holds data needed to populate db models
    """

    gene_data = {}

    # fetching all genes information from PanelApp Panel
    for gene in panel.data.get("genes", []):
        hgnc_id = gene.get("gene_data", {}).get("hgnc_id")
        if hgnc_id:
            gene_data[hgnc_id] = gene

    # fetching all confidence 3 genes
    for gene in panel.genes.get("3", []):
        hgnc_id = gene.get("hgnc_id")

        if not hgnc_id:
            print(f"Skipping {gene}. No HGNC id found.")
            continue

        gene_info = gene_data.get(hgnc_id, {})

        gene_dict = {
            "transcript": _clean_val(gene_info.get("transcript")),
            "hgnc_id": hgnc_id,
            "confidence_level": gene_info.get("confidence_level"),
            "mode_of_inheritance": _clean_val(gene_info.get("mode_of_inheritance")),
            "mode_of_pathogenicity": _clean_val(gene_info.get("mode_of_pathogenicity")),
            "penetrance": _clean_val(gene_info.get("penetrance")),
            "gene_justification": "PanelApp",
            "transcript_justification": "PanelApp",
            "alias_symbols": _clean_val(gene_info["gene_data"].get("alias", None)),
            "gene_symbol": gene_info["gene_data"].get("gene_symbol"),
        }

        info_dict["genes"].append(gene_dict)

    return info_dict


def _add_region_info(panel: Panel, info_dict: dict):
    """
    Iterate over every region in the panel and retrieve the data

    args:
        panel [Panel]: PanelApp data for one panel
        info_dict [dict]: holds data needed to populate db models
    """

    if panel.data.get("regions"):
        for region in panel.data["regions"]:
            # only add confidence level 3 regions
            if region.get("confidence_level") == "3":
                # define start and end coordinates grch37
                if not region.get("grch37_coordinates"):
                    start_37, end_37 = None, None
                else:
                    start_37, end_37 = region.get("grch37_coordinates")

                # define start and end coordinates grch38
                if not region.get("grch38_coordinates"):
                    start_38, end_38 = None, None
                else:
                    start_38, end_38 = region.get("grch38_coordinates")

                region_dict = {
                    "confidence_level": region.get("confidence_level"),
                    "mode_of_inheritance": _clean_val(
                        region.get("mode_of_inheritance")
                    ),
                    "mode_of_pathogenicity": _clean_val(
                        region.get("mode_of_pathogenicity")
                    ),
                    "penetrance": _clean_val(region.get("penetrance")),
                    "name": region.get("verbose_name"),
                    "chrom": region.get("chromosome"),
                    "start_37": start_37,
                    "end_37": end_37,
                    "start_38": start_38,
                    "end_38": end_38,
                    "type": "CNV",  # all PA regions are CNVs
                    "variant_type": _clean_val(region.get("type_of_variants")),
                    "required_overlap": _clean_val(
                        region.get("required_overlap_percentage")
                    ),
                    "haploinsufficiency": _clean_val(
                        region.get("haploinsufficiency_score")
                    ),
                    "triplosensitivity": _clean_val(
                        region.get("triplosensitivity_score")
                    ),
                    "justification": "PanelApp",
                }

                info_dict["regions"].append(region_dict)

    return info_dict


def _parse_pa_panel_as_dict(panel: dict) -> dict:
    """
    Parses output of single-panel fetching method, which is a dict
    Returns an information dictionary.
    """
    panel = panel["results"]
    if len(panel) != 1:
        print(f"Error with panel id {panel.id}. More than one result returned")
    panel = panel[0]

    try:
        name = panel["name"]
    except KeyError:
        print(f"Error with panel id {panel.id}. Panel has no name")
        return {}

    try:
        version = panel["version"]
    except KeyError:
        print(f"Error with panel id {panel.id}. Panel has no version")
        return {}

    try:
        panel_id = panel["id"]
    except KeyError:
        print(f"Error with panel name {panel.id}. Panel has no id")
        return {}

    info_dict = {
        "panel_source": "PanelApp",
        "panel_name": name,
        "external_id": panel_id,
        "panel_version": version,
        "genes": [],
        "regions": [],
    }

    as_panel_class = Panel(panel_id=panel_id, version=version)

    _add_gene_info(as_panel_class, info_dict)
    _add_region_info(as_panel_class, info_dict)

    return info_dict


def _parse_single_pa_panel(panel: Panel) -> dict:
    """
    Parse output of all-panel fetching function, which is a Panel object
    """
    if not hasattr(panel, "name"):
        print(f"Error with panel id {panel.id}. Panel has no name")
        return {}

    if not hasattr(panel, "version"):
        print(f"Error with panel id {panel.id}. Panel has no version")
        return {}

    if not hasattr(panel, "id"):
        print(f"Error with panel name {panel.id}. Panel has no id")
        return {}

    info_dict = {
        "panel_source": "PanelApp",
        "panel_name": panel.name,
        "external_id": panel.id,
        "panel_version": panel.version,
        "genes": [],
        "regions": [],
    }

    _add_gene_info(panel, info_dict)
    _add_region_info(panel, info_dict)

    return info_dict


def parse_all_pa_panels() -> list[dict]:
    """Get a list of IDs for all current PanelApp panels, then
    parse and import all of these panels to the DB.
    returns:
        parsed_data [list of parsed dict]: data dicts for all panels
    """

    print("Fetching data for all PanelApp panels...")

    parsed_data = []

    all_panels: dict[int, Panel] = queries.get_all_signedoff_panels()

    for _, panel in all_panels.items():
        panel_data = _parse_single_pa_panel(panel)
        if not panel_data:
            continue
        parsed_data.append(panel_data)

    print("Data parsing completed.")

    return parsed_data


def parse_specified_pa_panels(panel_id: str) -> list:
    """
    For panels specified by name, get IDs and other information for the most recent
    signed-off version(s). An 'all' option will call all panels instead.
    Parse and import the panels to the DB
    params:
        panel_ids
    returns:
        parsed_data [list of dicts]: data dicts for all panels
    """

    print("Fetching data for requested PanelApp panels...")

    parsed_data = []

    panel = queries.get_signedoff_panel(panel_id)
    if not panel:
        print(
            "Error fetching panel ID {} from PanelApp - it may not be valid".format(
                panel_id
            )
        )
        return None

    print("Fetched {} panels".format(panel["count"]))

    panel_data = _parse_pa_panel_as_dict(panel)

    if not panel_data:
        print("Parsing failed for panel ID {}".format(panel_id))

    parsed_data.append(panel_data)

    print("Data parsing completed.")

    return parsed_data
