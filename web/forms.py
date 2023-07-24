from django import forms

from requests_app.models import ClinicalIndication, Panel


class ClinicalIndicationForm(forms.Form):
    r_code = forms.CharField(max_length=10)
    name = forms.CharField(max_length=250)
    test_method = forms.CharField(max_length=100)

    def clean_r_code(self):
        r_code: str = self.cleaned_data["r_code"]

        if not r_code.startswith("R"):
            self.add_error(
                "r_code",
                "Clinical Indication must start with uppercase letter R",
            )
            return

        try:
            ClinicalIndication.objects.get(r_code=r_code)
            self.add_error(
                "r_code",
                "R code already exist in database. Please use a different R code!",
            )
            return
        except ClinicalIndication.DoesNotExist:
            return r_code


class PanelForm(forms.Form):
    external_id = forms.CharField(max_length=30)
    name = forms.CharField(max_length=250)
    version = forms.CharField(max_length=10)

    def clean_external_id(self):
        external_id: str = self.cleaned_data["external_id"]

        try:
            Panel.objects.get(external_id=external_id)
            self.add_error(
                "external_id",
                "External ID already exist in database! Please modify existing PanelApp entry.",
            )
            return
        except ClinicalIndication.DoesNotExist:
            return external_id
