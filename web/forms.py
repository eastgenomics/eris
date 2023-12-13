import re
from django import forms

from requests_app.models import ClinicalIndication, Panel, Gene
from requests_app.management.commands.utils import sortable_version


class ClinicalIndicationForm(forms.Form):
    r_code = forms.CharField(max_length=10, required=True)
    name = forms.CharField(max_length=250, required=True)
    test_method = forms.CharField(max_length=500, required=False)

    def clean_r_code(self):
        r_code: str = self.cleaned_data["r_code"]

        # custom-made clinical indication doesn't necessarily need to start with R
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
    external_id = forms.CharField(max_length=30, required=False)
    panel_name = forms.CharField(max_length=250, required=True)
    panel_version = forms.CharField(max_length=10, required=False)

    def clean(self):
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
    hgnc_id = forms.CharField(max_length=30, required=True)
    gene_symbol = forms.CharField(max_length=30, required=False)

    def clean_hgnc_id(self):
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

    def clean_gene_symbol(self):
        gene_symbol = self.cleaned_data["gene_symbol"].strip().upper()

        try:
            Gene.objects.get(gene_symbol=gene_symbol)

            self.add_error(
                "gene_symbol",
                f"HGNC ID with gene symbol '{gene_symbol}' already exists!",
            )

        except:
            # no gene with this gene_symbol exists, that's good
            pass

        return gene_symbol
