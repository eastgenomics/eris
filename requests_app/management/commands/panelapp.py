import requests

from panel_requests.settings import PANELAPP_API_URL


class PanelClass:
    """
    Class for panel data. Greedy ingestion of all attributes from PanelApp API
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


def get_panel(panel_num: int, version: float = None) -> PanelClass:
    """
    Function to get individual panel and panel version

    :param panel_num: panel number
    :param version: panel version

    :return: PanelClass object
    """
    if version:
        panel_url = f"{PANELAPP_API_URL}{panel_num}/?version={version}&format=json"
    else:
        panel_url = f"{PANELAPP_API_URL}{panel_num}/?format=json"

    response = requests.get(panel_url)

    if response.status_code != 200:
        return None

    return PanelClass(**response.json())


def fetch_all_panels() -> list[PanelClass]:
    """
    Function to get all signed off panels

    :return: list of PanelClass objects
    """

    print("Fetching all PanelApp panels...")

    panels: list[PanelClass] = []

    for panel in _get_all_panel():
        panel_id = panel["id"]
        panel_version = panel.get("version")

        # fetching specific signed-off version
        panel_data = get_panel(panel_id, panel_version)

        if panel_data:
            panel_data.panel_source = "PanelApp"
            panels.append(panel_data)

    return panels
