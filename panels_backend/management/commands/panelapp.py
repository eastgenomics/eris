import requests

from core.settings import PANELAPP_API_URL


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

        self.child_panels: list[PanelClass] = []
        self._create_component_panels()

    def _create_component_panels(self) -> None:
        """
        Parse out component-panels from the API call.
        In a normal panel, the genes and regions are nested under the panel's
        overall info.
        But for superpanels, we find the panels by looking in 'panel' under
        each constituent gene or region, so we need to reorder everything
        in parsing.
        In addition: we need to find LATEST SIGNED OFF versions of each child-panel
        """
        children_panel_ids = set([g["panel"]["id"] for g in self.genes])

        for panel_id in children_panel_ids:
            latest_signed_off_version = (
                _fetch_latest_signed_off_version_based_on_panel_id(panel_id)
            )
            panel, _ = get_specific_version_panel(panel_id, latest_signed_off_version)

            self.child_panels.append(panel)


def _get_all_signed_off_panels() -> list[dict]:
    """
    Fetches all signed-off panels from the PanelApp API
    Handles weird pagination in PanelApp
    The panels have NOT YET been converted to PanelClass or SuperPanelClass objects

    :return: list of panels (dict)
    """
    all_panels = []

    panelapp_url = f"{PANELAPP_API_URL}signedoff?format=json"

    # panelapp returns a paginated response
    # if next is not None, there's more data to fetch
    while panelapp_url:
        response = requests.get(panelapp_url)
        if response.status_code != 200:
            print(
                f"Aborting because API returned a non-200 exit code: {response.status_code} {response.reason}"
            )
            exit(1)

        data = response.json()
        all_panels += data["results"]  # append to all_panels
        panelapp_url = data["next"]  # here we keep fetching until next is None

    return all_panels


def _fetch_latest_signed_off_version_based_on_panel_id(panel_id: int) -> str:
    """
    Fetch the latest signed-off version of a panel from PanelApp, based on its ID.
    :param: panel_id, a string
    :return: latest signed-off version of the panel, as a string
    """
    try:
        return requests.get(f"{PANELAPP_API_URL}signedoff/?panel_id={panel_id}").json()[
            "results"
        ][0]["version"]
    except Exception as e:
        raise Exception(
            f"Could not fetch latest signed off panel based on panel id {panel_id}. Error: {e}"
        )


def _check_superpanel_status(response: dict[str, str]) -> bool:
    """
    From the response data for a PanelApp panel API request,
    work out whether the panel is a standard panel or superpanel.
    Returns True if superpanel, otherwise False.
    """

    for row in response.get("types", []):
        if row["name"].strip().upper() == "SUPER PANEL":
            return True

    return False


def get_panel_from_url(panel_url) -> tuple[PanelClass | SuperPanelClass, bool]:
    """
    Get response from a PanelApp URL, handle error codes,
    work out whether the result is a panel or superpanel,
    and parse/return it appropriately.

    :param: panel_url, a pre-formatted URL for PanelApp
    :return: PanelClass object or SuperPanelClass
    :return: is_superpanel - True if panel is a superpanel, False otherwise
    """
    response = requests.get(panel_url)
    if response.status_code != 200:
        print(
            f"Aborting because API returned a non-200 exit code: {response.status_code}"
        )
        exit(1)

    is_superpanel = _check_superpanel_status(response.json())

    if not is_superpanel:
        return PanelClass(**response.json()), is_superpanel
    else:
        return SuperPanelClass(**response.json()), is_superpanel


def get_latest_version_panel(
    panel_num: int,
) -> tuple[PanelClass | SuperPanelClass, bool]:
    """
    Function to get LATEST version of a panel,
    regardless of whether it's signed off or not.
    Wraps get_panel_from_url() in a way which makes it easier to keep track of which API URL endpoints are used.

    :param panel_num: panel number
    :return: PanelClass object or SuperPanelClass
    :return: is_superpanel - True if panel is a superpanel, False otherwise
    """
    panel_url = f"{PANELAPP_API_URL}{panel_num}/?format=json"
    panel, is_superpanel = get_panel_from_url(panel_url)
    return panel, is_superpanel


def get_specific_version_panel(
    panel_num: int, version: float
) -> tuple[PanelClass | SuperPanelClass, bool]:
    """
    Function to get a specific version of an individual PanelApp panel, from the PanelAppAPI
    Wraps get_panel_from_url() in a way which makes it easier to keep track of which API URL endpoints are used.

    :param panel_num: panel number
    :param version: panel version
    :return: PanelClass object or SuperPanelClass
    :return: is_superpanel - True if panel is a superpanel, False otherwise
    """
    panel_url = f"{PANELAPP_API_URL}{panel_num}/?version={version}&format=json"
    panel, is_superpanel = get_panel_from_url(panel_url)
    return panel, is_superpanel


def process_all_signed_off_panels() -> tuple[list[PanelClass], list[SuperPanelClass]]:
    """
    Function to process all signed off panels and superpanels,
    starting by getting information from _get_all_signed_off_panels()

    :return: a list of PanelClass objects
    :return: a list of SuperPanelClass objects
    """

    print("Fetching all PanelApp panels...")

    panels: list[PanelClass] = []
    superpanels: list[SuperPanelClass] = []

    for panel in _get_all_signed_off_panels():
        panel_id = panel["id"]
        panel_version = panel.get("version")

        # fetching specific signed-off version
        panel_data, is_superpanel = get_specific_version_panel(panel_id, panel_version)
        if panel_data:
            panel_data.panel_source = "PanelApp"
            if is_superpanel:
                superpanels.append(panel_data)
            else:
                panels.append(panel_data)

    return panels, superpanels