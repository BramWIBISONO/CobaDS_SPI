from django import forms

from students.forms import DATE, BranchForm

from .services import TEACHER_STATUSES


class TeacherForm(BranchForm):
    name = forms.CharField(label="Nama guru", max_length=120, help_text="Tulis seperti dipakai di kelas, mis. Ms. Linda")
    status = forms.ChoiceField(label="Status", choices=[(s, s) for s in TEACHER_STATUSES])
    phone = forms.CharField(label="Telepon", required=False, max_length=40)
    email = forms.EmailField(label="Email", required=False)
    spec = forms.CharField(label="Spesialisasi", required=False, max_length=120)
    emp_type = forms.CharField(label="Jenis kerja", required=False, max_length=60, help_text="mis. Tetap, Paruh waktu")
    join = forms.DateField(label="Mulai bergabung", required=False, widget=DATE)

    sections = [("Guru", ["name", "status", "spec", "emp_type", "join"]), ("Kontak", ["phone", "email"])]
