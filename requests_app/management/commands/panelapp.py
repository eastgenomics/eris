import requests
import json

from panel_requests.settings import PANELAPP_API_URL


class PanelClass:
    """
    Class for panel data. Default population is by greedy ingestion of all
    attributes from PanelApp API. However, may also be populated by
    SuperPanelClass.
    """

    def __init__(self, **a):
        # common default attributes
        self.id: str = None
        self.name: str = None
        self.version: str = None
        self.panel_source: str = None
        self.genes: list[dict] = []
        self.regions: list[dict] = []
        self.types: list[dict] = []
        [setattr(self, key, a[key]) for key in a]


class SuperPanelClass:
    """
    Class for superpanel data, which ingests from PanelApp API.
    Will contain PanelClass objects.
    """

    def __init__(self, **a):
        # common default attributes
        self.id: str = None
        self.name: str = None
        self.version: str = None
        self.panel_source: str = None
        self.genes: list[dict] = []
        self.regions: list[dict] = []
        self.types: list[dict] = []
        [setattr(self, key, a[key]) for key in a]

        self.child_panels = self.create_component_panels(self.genes,
                                                         self.regions)

    def create_component_panels(self, genes, regions):
        """
        Parse out component-panels from the API call.
        In a normal panel, the genes and regions are nested under the panel's
        overall info.
        But for superpanels, we find the panels by looking in 'panel' under
        each constituent gene or region, so we need to reorder everything
        in parsing.
        """
        panels = []

        for gene in genes:
            parent_panel = gene["panel"]
            panel_id = parent_panel["id"]
            # fetch this Panel if its in the panel-list already, otherwise,
            # make it
            component_panel = next((x for x in panels if x.id == panel_id),
                                   None)
            if component_panel:
                # append gene to the list associated with this panel
                component_panel.genes.append(gene)
            else:
                # create panel and append gene info to it
                component_panel = PanelClass()
                component_panel.id = panel_id
                component_panel.name = parent_panel["name"]
                component_panel.version = parent_panel["version"]
                # currently only use SuperPanelClass for PanelApp
                component_panel.panel_source = "PanelApp"
                # add this gene to the panel
                component_panel.genes.append(gene)
                panels.append(component_panel)

        for region in regions:
            parent_panel = region["panel"]
            panel_id = parent_panel["id"] 
            #TODO: how does this handle region(s) duplicated from multiple
            # panels?
            # fetch this Panel if its in the panel-list already, otherwise,
            # make it
            component_panel = next((x for x in panels if x.id == panel_id),
                                   None)
            if component_panel:
                # append region to the list associated with this panel
                component_panel.regions.append(region)
            else:
                # create panel and append region info to it
                component_panel = PanelClass()
                component_panel.id = panel_id
                component_panel.name = parent_panel["name"]
                component_panel.version = parent_panel["version"]

                # currently only use SuperPanelClass for PanelApp
                component_panel.panel_source = "PanelApp"
                # add this region to the panel
                component_panel.regions.append(region)
                panels.append(component_panel)
        return panels


def _get_all_panel(signed_off: bool = True) -> list[dict]:
    """
    Function to get all signed off panels

    :param signed_off: boolean to get signed off panels

    :return: list of panels (dict)
    """
    all_panels = []

    if signed_off:
        panelapp_url = f"{PANELAPP_API_URL}signedoff?format=json"
    else:
        panelapp_url = f"{PANELAPP_API_URL}?format=json"

    # panelapp return a paginated response
    # if next is not None, there's more data to fetch
    while panelapp_url:
        response = requests.get(panelapp_url)

        if response.status_code != 200:
            break

        data = response.json()
        all_panels += data["results"]  # append to all_panels
        panelapp_url = data["next"]  # here we keep fetching until next is None

    return all_panels


def _check_superpanel_status(response: requests.Response) -> bool:
    """
    From the response data for a PanelApp panel API request,
    work out whether the panel is a standard panel or superpanel.
    Returns True if superpanel, otherwise False.
    """
    is_superpanel = False
    data = response.json()
    for i in data["types"]:
        if i["name"] == "Super Panel":
            is_superpanel = True

    return is_superpanel


def get_panel(panel_num: int, version: float = None) -> \
    tuple[PanelClass | SuperPanelClass, bool]:
    """
    Function to get individual panel and panel version

    :param panel_num: panel number
    :param version: panel version

    :return: PanelClass object or SuperPanelClass
    :return: is_superpanel - True if panel is a superpanel, False otherwise
    """
    if version:
        panel_url = f"{PANELAPP_API_URL}{panel_num}/?version={version}&format=json"
    else:
        panel_url = f"{PANELAPP_API_URL}{panel_num}/?format=json"

    response = requests.get(panel_url)

    if response.status_code != 200:
        return None

    is_superpanel = _check_superpanel_status(response)

    if not is_superpanel:
        return PanelClass(**response.json()), is_superpanel
    else:
        return SuperPanelClass(**response.json()), is_superpanel


def fetch_all_panels() -> tuple[list[PanelClass], list[SuperPanelClass]]:
    """
    Function to get all signed off panels

    :return: list of PanelClass objects
    :return: list of SuperPanelClass objects
    """

    print("Fetching all PanelApp panels...")

    panels: list[PanelClass] = []
    superpanels: list[SuperPanelClass] = []

    for panel in _get_all_panel():
        panel_id = panel["id"]
        panel_version = panel.get("version")

        # fetching specific signed-off version
        panel_data, is_superpanel = \
            get_panel(panel_id, panel_version)

        if panel_data:
            panel_data.panel_source = "PanelApp"
            if is_superpanel:
                superpanels.append(panel_data)
            else:
                panels.append(panel_data)

    return panels, superpanels
