from django import forms

from requests_app.models import ClinicalIndication, Panel


class ClinicalIndicationForm(forms.Form):
    r_code = forms.CharField(max_length=10)
    name = forms.CharField(max_length=250)
    test_method = forms.CharField(max_length=100, required=False)

    def clean_r_code(self):
        r_code: str = self.cleaned_data["r_code"]

        if not r_code.startswith("R"):
            self.add_error(
                "r_code",
                "Clinical Indication must start with uppercase letter R",
            )

        try:
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
    panel_name = forms.CharField(max_length=250)
    panel_version = forms.CharField(max_length=10, required=False)

    def clean_panel_name(self):
        panel_name: str = self.cleaned_data["panel_name"]

        # clean input
        if "HGNC" in panel_name and "," in panel_name:
            # dealing with HGNC type panel
            panel_name = ",".join([hgnc.strip() for hgnc in panel_name.split(",")])
        else:
            panel_name = panel_name.strip()

        p = Panel.objects.filter(panel_name__iexact=panel_name)

        if p:
            self.add_error(
                "panel_name",
                "There is an existing panel with this name! Please modify existing entry.",
            )

        return panel_name
