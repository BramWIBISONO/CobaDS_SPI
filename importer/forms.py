from django import forms

MAX_UPLOAD_MB = 40


class UploadForm(forms.Form):
    file = forms.FileField(label="Workbook SPI v4 (.xlsm / .xlsx)")

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.lower().endswith((".xlsm", ".xlsx")):
            raise forms.ValidationError("Pilih file Excel .xlsm atau .xlsx (workbook SPI v4).")
        if f.size > MAX_UPLOAD_MB * 1024 * 1024:
            raise forms.ValidationError(f"File lebih besar dari {MAX_UPLOAD_MB} MB.")
        return f
