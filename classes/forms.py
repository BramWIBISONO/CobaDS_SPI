from django import forms
from django.utils import timezone

from students.forms import DATE, BranchForm, level_choices, program_choices, teacher_choices

from .services import DAYS, TYPE_LETTER

TIME = forms.TimeInput(attrs={"type": "time"}, format="%H:%M")
MODES = [("OnSite", "OnSite"), ("OnLine", "OnLine")]


class ClassCreateForm(BranchForm):
    code = forms.CharField(label="Kode kelas", max_length=30, help_text="Huruf pertama = tipe: F Focus, P Partner, G Group, S School.")
    tipe = forms.ChoiceField(label="Tipe kelas", choices=[(t, t) for t in TYPE_LETTER])
    program = forms.ChoiceField(label="Program", required=False)
    level = forms.ChoiceField(label="Level", required=False)
    guru = forms.ChoiceField(label="Guru", required=False)
    mode = forms.ChoiceField(label="Mode", choices=MODES)
    bahasa = forms.CharField(label="Bahasa", required=False, max_length=40)
    start = forms.DateField(label="Mulai", required=False, widget=DATE)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["program"].choices = program_choices(self.branch)
        self.fields["level"].choices = level_choices(self.branch)
        self.fields["guru"].choices = [("", "— belum ada —")] + teacher_choices(self.branch)[1:]
        self.fields["start"].initial = timezone.localdate()


class ClassEditForm(BranchForm):
    program = forms.ChoiceField(label="Program", required=False)
    level = forms.ChoiceField(label="Level", required=False)
    mode = forms.ChoiceField(label="Mode", choices=MODES)
    bahasa = forms.CharField(label="Bahasa", required=False, max_length=40)
    start = forms.DateField(label="Mulai", required=False, widget=DATE)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["program"].choices = program_choices(self.branch)
        self.fields["level"].choices = level_choices(self.branch)


class AssignTeacherForm(BranchForm):
    guru = forms.ChoiceField(label="Guru kelas")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["guru"].choices = teacher_choices(self.branch)[1:]


class AddMemberForm(BranchForm):
    std = forms.CharField(label="Student ID", max_length=40)
    tanggal = forms.DateField(label="Mulai di kelas ini", widget=DATE)
    allow_over_capacity = forms.BooleanField(label="Izinkan melebihi kapasitas", required=False)

    def __init__(self, *args, can_over_capacity=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tanggal"].initial = timezone.localdate()
        if not can_over_capacity:
            del self.fields["allow_over_capacity"]


class SlotForm(BranchForm):
    day = forms.ChoiceField(label="Hari", choices=[(d, d.title()) for d in DAYS])
    start = forms.TimeField(label="Mulai", widget=TIME)
    end = forms.TimeField(label="Selesai", widget=TIME)
    room = forms.CharField(label="Ruang", required=False, max_length=60)
    teacher = forms.ChoiceField(label="Guru (kosong = guru kelas)", required=False)
    eff_from = forms.DateField(label="Berlaku mulai", required=False, widget=DATE)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["teacher"].choices = teacher_choices(self.branch)


class GenerateForm(BranchForm):
    start = forms.DateField(label="Dari tanggal", widget=DATE)
    end = forms.DateField(label="Sampai tanggal", widget=DATE)

    def clean(self):
        data = super().clean()
        s, e = data.get("start"), data.get("end")
        if s and e and (e < s or (e - s).days > 62):
            raise forms.ValidationError("Rentang tanggal harus maju dan paling lama 2 bulan.")
        return data
