import re
from django import forms

from panels_backend.models import ClinicalIndication, Panel, Gene
from panels_backend.management.commands.utils import sortable_version


class ClinicalIndicationForm(forms.Form):
    """
    Form to parse Clinical Indication data from the user.

    """

    r_code = forms.CharField(max_length=10, required=True)
    name = forms.CharField(max_length=250, required=True)
    test_method = forms.CharField(max_length=500, required=False)

    def clean_r_code(self):
        """
        There can only be one R code for each clinical indication.
        This check if the input R code exist in the database or not.

        If exist: raise error
        """
        r_code: str = self.cleaned_data["r_code"]

        # NOTE: custom-made clinical indication doesn't necessarily need to start with R
        try:  # query if there is an existing clinical indication with this r_code
            ClinicalIndication.objects.get(r_code=r_code)
            self.add_error(
                "r_code",
                "There is an existing clinical indication with this R code! Please modify existing entry.",
            )
        except ClinicalIndication.DoesNotExist:
            pass

        return r_code


class PanelForm(forms.Form):
    """
    Form to parse Panel data from the user.
    """

    external_id = forms.CharField(max_length=30, required=False)
    panel_name = forms.CharField(max_length=250, required=True)
    panel_version = forms.CharField(max_length=10, required=False)

    def clean(self):
        """
        Two validations for panel submissions:
        1. Check if the panel name already exists in the database. If yes, raise error.
        2. Check if the external ID and panel version already exists in the database. If yes, raise error.

        NOTE: one external ID can have multiple panel versions, but there can
        only be one unique combination of external ID and panel version.
        """

        cleaned_data = super().clean()
        external_id = cleaned_data.get("external_id")
        panel_version = cleaned_data.get("panel_version")
        panel_name: str = self.cleaned_data.get("panel_name")

        if panel_name:
            p = Panel.objects.filter(panel_name__iexact=panel_name)

            if p:
                self.add_error(
                    "panel_name",
                    "There is an existing panel with this name! Please modify existing entry.",
                )

        if external_id and panel_version:
            p = Panel.objects.filter(
                external_id__iexact=external_id,
                panel_version__iexact=sortable_version(panel_version),
            )

            if p:
                self.add_error(
                    "external_id",
                    "There is an existing panel with this external ID and version! Please modify existing entry.",
                )


class GeneForm(forms.Form):
    """
    Form to parse Gene data from the user.
    """

    hgnc_id = forms.CharField(max_length=30, required=True)
    gene_symbol = forms.CharField(max_length=30, required=False)

    def clean_hgnc_id(self):
        """
        A few validations for HGNC ID:
        1. HGNC ID cannot be empty
        2. HGNC ID must start with 'HGNC:'
        3. HGNC ID must be followed by numbers
        4. HGNC ID must not exist in the database already

        NOTE: HGNC ID is unique - gene symbol is not, thus a check on whether
        the gene symbol already exists in the database is not necessary.
        """
        hgnc_id: str = self.cleaned_data["hgnc_id"].upper()

        if not hgnc_id:
            self.add_error("hgnc_id", "HGNC ID cannot be empty!")

        if not hgnc_id.startswith("HGNC:"):
            self.add_error("hgnc_id", "HGNC ID must start with 'HGNC:'")

        if not re.match(r"^[0-9]+$", hgnc_id[5:]):
            self.add_error("hgnc_id", "HGNC ID must be followed by numbers!")

        try:
            Gene.objects.get(hgnc_id=hgnc_id)

            self.add_error(
                "hgnc_id", f"Gene with HGNC ID '{hgnc_id}' already exists in db!"
            )
        except Gene.DoesNotExist:
            # no gene with this hgnc_id exists, that's good
            pass

        return hgnc_id
