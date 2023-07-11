from django import forms

from requests_app.models import ClinicalIndication


class ClinicalIndicationForm(forms.Form):
    r_code = forms.CharField(max_length=10)
    name = forms.CharField(max_length=250)
    test_method = forms.CharField(max_length=100)

    def clean_r_code(self):
        r_code: str = self.cleaned_data["r_code"]
        try:
            ClinicalIndication.objects.get(r_code=r_code)
            self.add_error("r_code", "Clinical Indication already exists")
            # raise ValueError("Clinical Indication already exists")
            pass
        except ClinicalIndication.DoesNotExist:
            return r_code
