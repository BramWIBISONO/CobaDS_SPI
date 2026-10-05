"""Layanan murid: semua perubahan data murid lewat sini (validasi, transaksi, ID baru, AUDIT_LOG).
Aturan mengikuti INPUT CENTER v4 (Murid Baru, Update Murid, Perubahan Status, Follow Up) - docs/ARCHITECTURE.md."""
import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from classes.models import ClassMaster, ClassMembers
from core import audit
from core.ids import next_id, next_row_no
from core.notifications import notify
from core.records import apply_changes
from dashboards.calc.base import BranchData, fold, period_code
from dashboards.calc.kelas import kapasitas
from dashboards.calc.status import kode_dipakai, semua_status_sekarang, status_sekarang
from finance.models import Periode
from masterdata.models import ProgramMaster, TeacherMaster

from .models import CatatanMurid, FollowUp, ParentMaster, StatusEvent, StudentMaster, StudentOff

STATUSES = ["ACTIVE", "ON LEAVE", "OFF", "PENDING", "ALUMNI/INACTIVE"]
STATUS_LABEL = {"ACTIVE": "Aktif", "ON LEAVE": "Cuti", "OFF": "OFF", "PENDING": "Pending", "ALUMNI/INACTIVE": "Alumni / tidak aktif"}
NEW_STUDENT_STATUSES = ["ACTIVE", "PENDING"]
FU_STATUSES = ["Terbuka", "Dikerjakan", "Menunggu", "Selesai", "Dibatalkan"]
FU_DONE = {"selesai", "dibatalkan"}
FU_PRIORITIES = ["MENDESAK", "TINGGI", "NORMAL", "RENDAH"]
SOURCE = "APLIKASI"


class DuplicateStudent(ValidationError):
    """Nama (dan tanggal lahir) sama dengan murid yang sudah ada - perlu konfirmasi sengaja."""


class ClassFull(ValidationError):
    """Murid aktif di kelas sudah mencapai kapasitas."""


def _today(today):
    return today or timezone.localdate()


def _norm_name(name):
    return " ".join(str(name or "").split()).casefold()


def dipakai(s):
    """Nilai 'dipakai' STUDENT_MASTER: kolom (ubah) bila terisi, selain itu nilai sumber."""
    return {"program": s.prog_in or s.program, "level": s.level_in or s.level, "kode": kode_dipakai(s),
            "guru": s.guru_in or s.guru, "harga": s.harga_in if s.harga_in is not None else s.harga,
            "sekolah": s.sekolah_in or s.sekolah}


def get_student(branch, std):
    try:
        return StudentMaster.objects.for_branch(branch).get(std=std)
    except StudentMaster.DoesNotExist as exc:
        raise ValidationError(f"Murid {std} tidak ada di cabang ini.") from exc


def period_status(branch, d):
    row = Periode.objects.for_branch(branch).filter(per=period_code(d)).first()
    return (row.status or "").upper() if row else ""


def ensure_open(branch, d, what="Perubahan"):
    if period_status(branch, d) == "CLOSED":
        raise ValidationError(f"{what} tanggal {d:%d %b %Y} ada di periode CLOSED - pilih tanggal di periode yang masih terbuka.")


def find_parent(branch, pid):
    row = ParentMaster.objects.for_branch(branch).filter(pid=pid).first()
    if row is None:
        raise ValidationError(f"Orang tua {pid} tidak ada di cabang ini.")
    return row


def find_class(branch, kode):
    row = ClassMaster.objects.for_branch(branch).filter(code__iexact=str(kode).strip()).first()
    if row is None:
        raise ValidationError(f"Kode kelas {kode} belum ada di daftar kelas - buat kelasnya dulu di menu Kelas.")
    return row


def find_teacher(branch, name):
    key = fold(" ".join(str(name).split()))
    row = next((t for t in TeacherMaster.objects.for_branch(branch) if fold(t.name) == key), None)
    if row is None:
        raise ValidationError(f"Guru {name} tidak ada di daftar guru - tambahkan dulu di menu Guru.")
    return row


def check_program(branch, program, level):
    if not program and not level:
        return
    rows = list(ProgramMaster.objects.for_branch(branch).values_list("program", "level"))
    if not rows:
        return                                                     # cabang tanpa daftar program: tidak divalidasi
    if program and not any(fold(p) == fold(program) for p, _ in rows):
        raise ValidationError(f"Program {program} tidak ada di daftar program.")
    if level and not any(fold(p) == fold(program) and fold(lv) == fold(level) for p, lv in rows):
        raise ValidationError(f"Level {level} bukan bagian program {program}.")


def check_capacity(branch, kode, std, today, allow):
    """Murid ACTIVE di kelas (kode dipakai) tidak boleh melebihi kapasitas SETTINGS kecuali izin khusus."""
    data = BranchData(branch, today)
    cap = kapasitas(data, kode)
    if not isinstance(cap, (int, float)) or allow:
        return
    st = semua_status_sekarang(data)
    n = sum(1 for s in data.students if s.std and s.std != std and fold(kode_dipakai(s)) == fold(kode)
            and fold(st.get(fold(s.std))) == "active")
    if n + 1 > cap:
        raise ClassFull(f"Kelas {kode} penuh: {n} murid aktif dari kapasitas {int(cap)}. Pilih kelas lain atau minta Branch Admin.")


def _update(branch, user, obj, entity, entity_id, changes):
    return apply_changes(branch, user, obj, entity, entity_id, changes)


def _move_membership(branch, user, student, cls, tanggal):
    for m in ClassMembers.objects.for_branch(branch).filter(std=student.std, status="CURRENT").exclude(code__iexact=cls.code):
        m.status, m.end = "ENDED", tanggal
        m.save(update_fields=["status", "end"])
        audit.log(branch=branch, user=user, action="UPDATE", entity="CLASS_MEMBERS", entity_id=m.mbr, field="Status Membership",
                  old="CURRENT", new=f"ENDED ({tanggal:%d %b %Y})")
    if ClassMembers.objects.for_branch(branch).filter(std=student.std, code__iexact=cls.code, status="CURRENT").exists():
        return
    mbr = next_id(ClassMembers, "mbr", "MBR-APP-", 6, branch)
    ClassMembers.objects.create(branch=branch, row_no=next_row_no(ClassMembers, branch), mbr=mbr, code=cls.code, class_id=cls.class_id,
                                std=student.std, nama=student.nama, status="CURRENT", status_plain="Kelas saat ini", start=tanggal,
                                program=cls.program, level=cls.level, guru=cls.guru, mode=cls.mode, sources_plain=SOURCE)
    audit.log(branch=branch, user=user, action="CREATE", entity="CLASS_MEMBERS", entity_id=mbr, field="Kelas", new=f"{student.std} -> {cls.code}")


def _new_parent(branch, user, nama, hub="", wa="", email=""):
    pid = next_id(ParentMaster, "pid", "PAR-", 5, branch)
    parent = ParentMaster.objects.create(branch=branch, row_no=next_row_no(ParentMaster, branch), pid=pid, nama=nama.strip(), hub=hub,
                                         wa=wa, email=email, sumber=SOURCE)
    audit.log(branch=branch, user=user, action="CREATE", entity="PARENT_MASTER", entity_id=pid, field="Nama Orang Tua", new=parent.nama)
    return parent


def _event(branch, user, std, tgl, status, jenis, alasan="", konfirm="Ya", kembali=None):
    eid = next_id(StatusEvent, "eid", "EVT-", 6, branch)
    ev = StatusEvent.objects.create(branch=branch, row_no=next_row_no(StatusEvent, branch), eid=eid, tgl=tgl, std=std, status=status,
                                    jenis=jenis, alasan=alasan, kembali=kembali, konfirm=konfirm, oleh=audit.actor_name(user),
                                    pada=timezone.now(), sumber=SOURCE)
    audit.log(branch=branch, user=user, action="CREATE", entity="STATUS_EVENT", entity_id=eid, field="Status Baru",
              new=f"{std} -> {status} ({tgl:%d %b %Y})")
    return ev


def find_duplicates(branch, nama, lahir=None, exclude_std=None):
    key = _norm_name(nama)
    out = []
    for s in StudentMaster.objects.for_branch(branch).exclude(std=exclude_std or ""):
        if _norm_name(s.nama) == key and (lahir is None or s.lahir is None or s.lahir == lahir):
            out.append(s)
    return out


@transaction.atomic
def create_student(branch, user, *, nama, mulai, status, lahir=None, hp="", sekolah="", program="", level="", kode="", guru="",
                   harga=None, catatan="", ortu_pid="", ortu_nama="", ortu_hub="", ortu_wa="", ortu_email="",
                   allow_duplicate=False, allow_over_capacity=False, today=None):
    today = _today(today)
    nama = " ".join(str(nama or "").split())
    if not nama:
        raise ValidationError("Nama murid wajib diisi.")
    if status not in NEW_STUDENT_STATUSES:
        raise ValidationError("Status awal murid baru: ACTIVE atau PENDING.")
    if not allow_duplicate:
        dup = find_duplicates(branch, nama, lahir)
        if dup:
            raise DuplicateStudent(f"Sudah ada murid bernama {dup[0].nama} ({dup[0].std}). Centang 'tetap simpan' bila memang murid berbeda.")
    parent = find_parent(branch, ortu_pid) if ortu_pid else None
    cls = find_class(branch, kode) if kode else None
    if guru:
        guru = find_teacher(branch, guru).name
    elif cls is not None and cls.guru:
        guru = cls.guru
    check_program(branch, program or (cls.program if cls else ""), level or (cls.level if cls else ""))
    ensure_open(branch, mulai, "Tanggal mulai")
    std = next_id(StudentMaster, "std", "STD-", 6, branch)
    if cls is not None and status == "ACTIVE":
        check_capacity(branch, cls.code, std, today, allow_over_capacity)
    if parent is None and ortu_nama.strip():
        parent = _new_parent(branch, user, ortu_nama, ortu_hub, ortu_wa, ortu_email)
    student = StudentMaster.objects.create(
        branch=branch, row_no=next_row_no(StudentMaster, branch), std=std, nama=nama, nama_asli=nama, unit=branch.unit_id, join=mulai,
        prog_in=program or (cls.program if cls else ""), level_in=level or (cls.level if cls else ""), kode_in=cls.code if cls else "",
        guru_in=guru, sekolah_in=sekolah, harga_in=harga, lahir=lahir, hp=hp, par=parent.pid if parent else "",
        mode=cls.mode if cls else "", prov_type=SOURCE)
    audit.log(branch=branch, user=user, action="CREATE", entity="STUDENT_MASTER", entity_id=std, field="Murid baru", new=f"{nama} ({status})")
    _event(branch, user, std, mulai, status, "MASUK", "Murid baru" + (f": {catatan}" if catatan else ""))
    if cls is not None:
        _move_membership(branch, user, student, cls, mulai)
    return student


EDITABLE = {"nama": "nama", "lahir": "lahir", "hp": "hp", "sekolah": "sekolah_in", "harga": "harga_in", "ortu_pid": "par"}


@transaction.atomic
def update_student(branch, user, std, **fields):
    student = get_student(branch, std)
    changes = {}
    for key, value in fields.items():
        if key not in EDITABLE:
            raise ValidationError(f"Kolom {key} tidak bisa diubah di sini.")
        if key == "nama":
            value = " ".join(str(value or "").split())
            if not value:
                raise ValidationError("Nama murid wajib diisi.")
        if key == "ortu_pid" and value:
            find_parent(branch, value)
        changes[EDITABLE[key]] = value
    return _update(branch, user, student, "STUDENT_MASTER", std, changes)


def _jenis(old, new):
    if new == "ACTIVE":
        return {"ON LEAVE": "AKTIF KEMBALI (CUTI SELESAI)", "OFF": "AKTIF KEMBALI (REJOIN)", "PENDING": "KONFIRMASI AKTIF"}.get(old, "KOREKSI")
    return {"ON LEAVE": "CUTI", "OFF": "OFF", "ALUMNI/INACTIVE": "ALUMNI"}.get(new, "PENDING")


@transaction.atomic
def change_status(branch, user, std, *, status, tanggal, alasan="", kategori="", kembali=None, konfirmasi=True, catatan="", today=None):
    today = _today(today)
    if status not in STATUSES:
        raise ValidationError("Status tidak dikenal.")
    student = get_student(branch, std)
    old = status_sekarang(BranchData(branch, today), student)
    if old == status:
        raise ValidationError(f"Status {student.nama} sudah {STATUS_LABEL.get(status, status)}.")
    ensure_open(branch, tanggal, "Tanggal efektif")
    text = " ".join(x for x in (alasan.strip(), f"[{kategori}]" if kategori else "", f"- {catatan}" if catatan else "") if x)
    konf = "Belum" if status == "ON LEAVE" and not konfirmasi else "Ya"
    ev = _event(branch, user, std, tanggal, status, _jenis(old, status), text, konf, kembali)
    if status == "OFF":
        off_id = f"OFF-{std[4:]}-{tanggal:%Y%m}"
        if not StudentOff.objects.for_branch(branch).filter(off_id=off_id).exists():
            d = dipakai(student)
            StudentOff.objects.create(
                branch=branch, row_no=next_row_no(StudentOff, branch), off_id=off_id, nama=student.nama, std=std,
                month=tanggal.replace(day=1), tgl=tanggal, alasan=f"{alasan.strip()} ({SOURCE})" if alasan.strip() else "UNKNOWN",
                kat_in=kategori, kode=d["kode"] or "MISSING", program=d["program"], level=d["level"], guru=d["guru"],
                sekolah=d["sekolah"], sumber=SOURCE, tgl_src=f"{SOURCE} (tanggal efektif)", v1=student.v1)
            audit.log(branch=branch, user=user, action="CREATE", entity="STUDENT_OFF", entity_id=off_id, field="Kejadian Off", new=std)
    return ev


@transaction.atomic
def change_class(branch, user, std, *, kode, tanggal, today=None, allow_over_capacity=False):
    today = _today(today)
    student = get_student(branch, std)
    cls = find_class(branch, kode)
    if fold(kode_dipakai(student)) == fold(cls.code):
        raise ValidationError(f"{student.nama} sudah di kelas {cls.code}.")
    ensure_open(branch, tanggal, "Tanggal pindah")
    if status_sekarang(BranchData(branch, today), student) == "ACTIVE":
        check_capacity(branch, cls.code, std, today, allow_over_capacity)
    changes = {"kode_in": cls.code}
    if cls.guru:
        changes["guru_in"] = cls.guru
    _update(branch, user, student, "STUDENT_MASTER", std, changes)
    _move_membership(branch, user, student, cls, tanggal)
    return student


@transaction.atomic
def change_teacher(branch, user, std, *, guru):
    student = get_student(branch, std)
    return _update(branch, user, student, "STUDENT_MASTER", std, {"guru_in": find_teacher(branch, guru).name})


@transaction.atomic
def change_program(branch, user, std, *, program, level):
    student = get_student(branch, std)
    check_program(branch, program, level)
    return _update(branch, user, student, "STUDENT_MASTER", std, {"prog_in": program, "level_in": level})


@transaction.atomic
def add_note(branch, user, std, teks):
    get_student(branch, std)
    teks = str(teks or "").strip()
    if not teks:
        raise ValidationError("Catatan kosong - tulis isinya dulu.")
    note = CatatanMurid.objects.create(branch=branch, std=std, teks=teks, dibuat_oleh=user)
    audit.log(branch=branch, user=user, action="CREATE", entity="CATATAN", entity_id=std, field="Catatan", new=teks[:200])
    return note


def followup_url(fid):
    return reverse("students:followup_detail", args=[fid])


@transaction.atomic
def create_followup(branch, user, *, jenis, std="", lead="", aksi="", catatan="", jatuh_tempo=None, prioritas="NORMAL",
                    ditugaskan=None, today=None):
    today = _today(today)
    if std:
        get_student(branch, std)
    if not (jenis or "").strip():
        raise ValidationError("Jenis follow-up wajib diisi.")
    if prioritas not in FU_PRIORITIES:
        raise ValidationError("Prioritas tidak dikenal.")
    fid = next_id(FollowUp, "fid", "FU-", 6, branch)
    fu = FollowUp.objects.create(
        branch=branch, row_no=next_row_no(FollowUp, branch), fid=fid, tgl=today, jenis=jenis.strip(), std=std, lead=lead,
        pic=audit.actor_name(ditugaskan) if ditugaskan else "", status="Terbuka", aksi=aksi, catatan=catatan, next=jatuh_tempo,
        oleh=audit.actor_name(user), pada=timezone.now(), sumber=SOURCE, prioritas=prioritas, ditugaskan=ditugaskan)
    audit.log(branch=branch, user=user, action="CREATE", entity="FOLLOW_UP", entity_id=fid, field="Follow-up",
              new=f"{std or lead} {jenis} ({prioritas})")
    if ditugaskan is not None and ditugaskan != user:
        notify(ditugaskan, branch, f"Follow-up baru untuk Anda: {jenis}",
               f"{fid} · {std or lead}" + (f" · jatuh tempo {jatuh_tempo:%d %b %Y}" if jatuh_tempo else ""),
               url=followup_url(fid), kind="followup")
    return fu


@transaction.atomic
def update_followup(branch, user, fid, *, status=None, catatan="", aksi=None, jatuh_tempo=..., prioritas=None, ditugaskan=...):
    fu = FollowUp.objects.for_branch(branch).filter(fid=fid).first()
    if fu is None:
        raise ValidationError(f"Follow-up {fid} tidak ada di cabang ini.")
    changes = {}
    if status is not None:
        if status not in FU_STATUSES:
            raise ValidationError("Status follow-up tidak dikenal.")
        changes["status"] = status
    if aksi is not None:
        changes["aksi"] = aksi
    if jatuh_tempo is not ...:
        changes["next"] = jatuh_tempo
    if prioritas is not None:
        if prioritas not in FU_PRIORITIES:
            raise ValidationError("Prioritas tidak dikenal.")
        changes["prioritas"] = prioritas
    if ditugaskan is not ...:
        changes["ditugaskan"] = ditugaskan
        changes["pic"] = audit.actor_name(ditugaskan) if ditugaskan else ""
    if catatan.strip():
        stamp = timezone.localtime().strftime("%d %b %Y %H:%M")
        changes["catatan"] = (f"{fu.catatan}\n" if fu.catatan else "") + f"[{stamp} · {audit.actor_name(user)}] {catatan.strip()}"
    old_assignee = fu.ditugaskan
    _update(branch, user, fu, "FOLLOW_UP", fid, changes)
    if status is not None and fold(status) in FU_DONE and fu.selesai_pada is None:
        fu.selesai_pada = timezone.now()
        fu.save(update_fields=["selesai_pada"])
    elif status is not None and fold(status) not in FU_DONE and fu.selesai_pada is not None:
        fu.selesai_pada = None
        fu.save(update_fields=["selesai_pada"])
    if ditugaskan is not ... and ditugaskan is not None and ditugaskan != old_assignee and ditugaskan != user:
        notify(ditugaskan, branch, f"Follow-up ditugaskan ke Anda: {fu.jenis}", f"{fid} · {fu.std or fu.lead}",
               url=followup_url(fid), kind="followup")
    return fu


def is_open_followup(fu):
    return fold(fu.status) not in FU_DONE


def due_bucket(due, today):
    """Pengelompokan jatuh tempo untuk Pusat Tindakan: TERLAMBAT / HARI INI / MINGGU INI / NANTI / TANPA TANGGAL."""
    if due is None:
        return "TANPA TANGGAL"
    if due < today:
        return "TERLAMBAT"
    if due == today:
        return "HARI INI"
    if due <= today + datetime.timedelta(days=7):
        return "MINGGU INI"
    return "NANTI"
