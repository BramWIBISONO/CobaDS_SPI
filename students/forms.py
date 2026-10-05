"""Form modul murid. Pilihan (kelas, guru, program, orang tua, pengguna) selalu dari cabang aktif."""
from django import forms
from django.utils import timezone

from accounts.models import User
from classes.models import ClassMaster
from dashboards.calc.base import fold
from masterdata.models import OffReasonMaster, ProgramMaster, TeacherMaster

from .services import FU_PRIORITIES, FU_STATUSES, NEW_STUDENT_STATUSES, STATUS_LABEL, STATUSES

DATE = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
FU_TYPES = ["SPP", "OFF", "Cuti", "Akademik", "Kehadiran", "Orang tua", "Lead", "Lainnya"]


def _choices(values, blank="— pilih —"):
    return [("", blank)] + [(v, v) for v in values]


def class_choices(branch):
    rows = ClassMaster.objects.for_branch(branch).exclude(code="").order_by("code").values_list("code", "tipe", "guru")
    return [("", "— tanpa kelas —")] + [(c, f"{c} · {t or '-'} · {g or 'guru belum ada'}") for c, t, g in rows]


def teacher_choices(branch):
    names = sorted({t.name for t in TeacherMaster.objects.for_branch(branch) if t.name and fold(t.status) != "inactive"})
    return _choices(names, "— ikut guru kelas —")


def program_choices(branch):
    return _choices(sorted({p for p in ProgramMaster.objects.for_branch(branch).values_list("program", flat=True) if p}))


def level_choices(branch):
    rows = ProgramMaster.objects.for_branch(branch).order_by("order", "level").values_list("level", flat=True)
    return _choices([lv for lv in rows if lv])


def staff_choices(branch):
    users = User.objects.filter(is_active=True, memberships__branch=branch).exclude(memberships__role="TEACHER").distinct()
    return [("", "— belum ditugaskan —")] + [(u.pk, u.display_name) for u in users.order_by("full_name")]


def off_categories(branch):
    rows = OffReasonMaster.objects.for_branch(branch)
    return sorted({(r.cat_final or r.cat) for r in rows if (r.cat_final or r.cat)})


class BranchForm(forms.Form):
    def __init__(self, *args, branch=None, **kwargs):
        self.branch = branch
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            if not isinstance(f.widget, (forms.CheckboxInput,)):
                f.widget.attrs.setdefault("class", "field")


class StudentCreateForm(BranchForm):
    nama = forms.CharField(label="Nama murid", max_length=150)
    lahir = forms.DateField(label="Tanggal lahir", required=False, widget=DATE)
    hp = forms.CharField(label="No. HP kontak", required=False, max_length=40)
    sekolah = forms.CharField(label="Sekolah", required=False, max_length=150)
    mulai = forms.DateField(label="Mulai belajar", widget=DATE)
    status = forms.ChoiceField(label="Status awal", choices=[(s, STATUS_LABEL[s]) for s in NEW_STUDENT_STATUSES])
    program = forms.ChoiceField(label="Program", required=False)
    level = forms.ChoiceField(label="Level", required=False)
    kode = forms.ChoiceField(label="Kelas", required=False)
    guru = forms.ChoiceField(label="Guru", required=False)
    harga = forms.DecimalField(label="Harga SPP per bulan (Rp)", required=False, min_value=0, max_digits=14, decimal_places=2)
    catatan = forms.CharField(label="Catatan", required=False, widget=forms.Textarea(attrs={"rows": 2}))
    ortu_pid = forms.CharField(label="Orang tua terdaftar (Parent ID)", required=False, max_length=20,
                               help_text="Isi bila orang tua sudah terdaftar (mis. kakak sudah belajar di SPI).")
    ortu_nama = forms.CharField(label="Nama orang tua baru", required=False, max_length=150)
    ortu_hub = forms.CharField(label="Hubungan", required=False, max_length=40)
    ortu_wa = forms.CharField(label="WhatsApp orang tua", required=False, max_length=40)
    ortu_email = forms.EmailField(label="Email orang tua", required=False)
    allow_duplicate = forms.BooleanField(label="Tetap simpan walau nama sama (murid berbeda)", required=False)
    allow_over_capacity = forms.BooleanField(label="Izinkan melebihi kapasitas kelas", required=False)

    def __init__(self, *args, can_over_capacity=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["program"].choices = program_choices(self.branch)
        self.fields["level"].choices = level_choices(self.branch)
        self.fields["kode"].choices = class_choices(self.branch)
        self.fields["guru"].choices = teacher_choices(self.branch)
        self.fields["mulai"].initial = timezone.localdate()
        if not can_over_capacity:
            del self.fields["allow_over_capacity"]

    def clean(self):
        data = super().clean()
        if data.get("ortu_pid") and data.get("ortu_nama"):
            self.add_error("ortu_nama", "Pilih salah satu: orang tua terdaftar ATAU orang tua baru.")
        return data


class StudentEditForm(BranchForm):
    nama = forms.CharField(label="Nama murid", max_length=150)
    lahir = forms.DateField(label="Tanggal lahir", required=False, widget=DATE)
    hp = forms.CharField(label="No. HP kontak", required=False, max_length=40)
    sekolah = forms.CharField(label="Sekolah (ubah)", required=False, max_length=150)
    harga = forms.DecimalField(label="Harga SPP per bulan (Rp)", required=False, min_value=0, max_digits=14, decimal_places=2)
    ortu_pid = forms.CharField(label="Parent ID orang tua", required=False, max_length=20)


class StatusForm(BranchForm):
    status = forms.ChoiceField(label="Status baru", choices=[(s, STATUS_LABEL[s]) for s in STATUSES])
    tanggal = forms.DateField(label="Tanggal efektif", widget=DATE)
    alasan = forms.CharField(label="Alasan", required=False, max_length=300)
    kategori = forms.CharField(label="Kategori alasan (untuk OFF)", required=False, max_length=120)
    kembali = forms.DateField(label="Perkiraan kembali (cuti)", required=False, widget=DATE)
    konfirmasi = forms.BooleanField(label="Sudah dikonfirmasi orang tua", required=False, initial=True)
    catatan = forms.CharField(label="Catatan", required=False, widget=forms.Textarea(attrs={"rows": 2}))
    buat_followup = forms.BooleanField(label="Buat follow-up ke orang tua (untuk OFF / cuti)", required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tanggal"].initial = timezone.localdate()

    def clean(self):
        data = super().clean()
        if data.get("status") == "OFF" and not (data.get("alasan") or "").strip():
            self.add_error("alasan", "Alasan OFF wajib diisi (dipakai analisis OFF & follow-up).")
        return data


class ClassForm(BranchForm):
    kode = forms.ChoiceField(label="Kelas baru")
    tanggal = forms.DateField(label="Mulai di kelas baru", widget=DATE)
    allow_over_capacity = forms.BooleanField(label="Izinkan melebihi kapasitas kelas", required=False)

    def __init__(self, *args, can_over_capacity=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kode"].choices = class_choices(self.branch)[1:]
        self.fields["tanggal"].initial = timezone.localdate()
        if not can_over_capacity:
            del self.fields["allow_over_capacity"]


class TeacherForm(BranchForm):
    guru = forms.ChoiceField(label="Guru")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["guru"].choices = teacher_choices(self.branch)[1:]


class ProgramForm(BranchForm):
    program = forms.ChoiceField(label="Program")
    level = forms.ChoiceField(label="Level")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["program"].choices = program_choices(self.branch)
        self.fields["level"].choices = level_choices(self.branch)


class NoteForm(forms.Form):
    teks = forms.CharField(label="Catatan baru", widget=forms.Textarea(attrs={"rows": 3, "class": "field"}), max_length=2000)


class FollowUpForm(BranchForm):
    std = forms.CharField(label="Student ID", required=False, max_length=40)
    jenis = forms.ChoiceField(label="Jenis", choices=_choices(FU_TYPES))
    aksi = forms.CharField(label="Tindak lanjut", required=False, max_length=200, help_text="mis. Hubungi orang tua, kirim pengingat SPP")
    catatan = forms.CharField(label="Catatan", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    jatuh_tempo = forms.DateField(label="Jatuh tempo", required=False, widget=DATE)
    prioritas = forms.ChoiceField(label="Prioritas", choices=[(p, p.title()) for p in FU_PRIORITIES], initial="NORMAL")
    ditugaskan = forms.ChoiceField(label="Ditugaskan ke", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ditugaskan"].choices = staff_choices(self.branch)

    def clean_ditugaskan(self):
        pk = self.cleaned_data.get("ditugaskan")
        if not pk:
            return None
        user = User.objects.filter(pk=pk, memberships__branch=self.branch).first()
        if user is None:
            raise forms.ValidationError("Pengguna tidak ada di cabang ini.")
        return user


class FollowUpUpdateForm(FollowUpForm):
    status = forms.ChoiceField(label="Status", choices=[(s, s) for s in FU_STATUSES])
    catatan = forms.CharField(label="Tambah catatan / hasil", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("std", "jenis"):
            del self.fields[name]
