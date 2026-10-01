import re

from django import forms

from .models import Branch

CODE_RE = re.compile(r"^SPI-[A-Z0-9]{2,12}$")


class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ["code", "name", "city", "address", "status", "language", "currency", "opening_date"]
        widgets = {"address": forms.Textarea(attrs={"rows": 2}),
                   "opening_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        if not CODE_RE.match(code):
            raise forms.ValidationError("Format Branch ID: SPI- lalu 2-12 huruf/angka, mis. SPI-AS.")
        if Branch.objects.filter(code__iexact=code).exists():
            raise forms.ValidationError("Branch ID ini sudah dipakai.")
        return code
