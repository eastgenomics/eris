"""
External python modules or scripts relavant to the web app
"""


class ChildPanelClass:
    """
    This class is used to store information about a child panel.
    Only used in the web app - GenePanel page.
    """

    def __init__(self, id: str, panel_name: str, panel_version: str) -> None:
        self.id = id
        self.panel_name = panel_name
        self.panel_version = panel_version


class GeneClass:
    """
    This class is used to store information about a gene.
    Only used in the web app - Gene page.
    Not to be confused with the Gene class in /requests_app/models.py
    """

    def __init__(self, id, hgnc) -> None:
        self.id = id
        self.hgnc = hgnc


class GenePanel:
    """
    This class is used to store information about a gene panel.
    Only used in the web app - GenePanel page.
    """

    def __init__(
        self,
        r_code: str,
        ci_name: str,
        ci_id: str,
        panel_id: str,
        panel_name: str,
        panel_version: str,
        hgncs: list[GeneClass],
        superpanel: bool = False,
        child_panels: list[ChildPanelClass] = [],
    ) -> None:
        self.ci_id = ci_id  # clinical indication id
        self.panel_id = panel_id  # panel id or superpanel id

        self.r_code = r_code
        self.ci_name = ci_name

        self.panel_name = panel_name
        self.panel_version = panel_version

        self.hgncs = hgncs  # list of GeneClass objects
        self.superpanel = superpanel  # deal with superpanel
        self.child_panels = child_panels  # deal with superpanel
