from django import forms
from django.utils import timezone

from .models import RUBRIK


class FinalProjectForm(forms.Form):
    judul = forms.CharField(label="Judul project", max_length=200, widget=forms.TextInput(attrs={"placeholder": "mis. Game Kejar Bintang dengan Python"}))
    tgl_selesai = forms.DateField(label="Tanggal presentasi / selesai", initial=timezone.localdate, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    link = forms.URLField(label="Link project (opsional)", required=False, assume_scheme="https",
                          widget=forms.URLInput(attrs={"placeholder": "https://..."}))
    deskripsi = forms.CharField(label="Deskripsi singkat", required=False, widget=forms.Textarea(attrs={"rows": 3}),
                                help_text="Apa yang dibuat murid dan konsep apa yang dipakai.")
    nilai_konsep = forms.IntegerField(label=RUBRIK[0][1], min_value=0, max_value=100)
    nilai_logika = forms.IntegerField(label=RUBRIK[1][1], min_value=0, max_value=100)
    nilai_kreativitas = forms.IntegerField(label=RUBRIK[2][1], min_value=0, max_value=100)
    nilai_presentasi = forms.IntegerField(label=RUBRIK[3][1], min_value=0, max_value=100)
    kekuatan = forms.CharField(label="Kekuatan murid", required=False, widget=forms.Textarea(attrs={"rows": 2}))
    perlu_ditingkatkan = forms.CharField(label="Yang perlu ditingkatkan", required=False, widget=forms.Textarea(attrs={"rows": 2}))
    catatan = forms.CharField(label="Catatan guru untuk orang tua", required=False, widget=forms.Textarea(attrs={"rows": 3}),
                              help_text="Tampil di Student Report.")
    rekomendasi = forms.CharField(label="Rekomendasi level berikutnya", required=False, max_length=80)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, f in self.fields.items():
            f.widget.attrs.setdefault("class", "field")
            if name.startswith("nilai_"):
                f.widget.attrs.update({"inputmode": "numeric", "placeholder": "0-100", "data-nilai": "1"})
