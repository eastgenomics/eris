"""
External python modules or scripts relavant to the web app
"""
from typing import List

class Genepanel:
    """
    Genepanel class for storing genepanel information
    Used for displaying genepanel information in the web app
    """

    def __init__(
        self,
        r_code: str,
        ci_name: str,
        panel_name: str,
        panel_version: str,
        hgncs: List[str],
    ) -> None:
        self.r_code = r_code
        self.ci_name = ci_name
        self.panel_name = panel_name
        self.panel_version = panel_version
        self.hgncs = hgncs
