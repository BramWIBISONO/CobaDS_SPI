"""Layanan guru (TEACHER_MASTER) dan pencocokan nama guru antar tabel (jadwal memakai 'BRAM', murid memakai 'Mr. Bram')."""
import re

from django.core.exceptions import ValidationError
from django.db import transaction

from core import audit
from core.ids import next_id, next_row_no
from core.records import apply_changes
from dashboards.calc.base import BranchData, as_date, fold
from dashboards.calc.status import semua_status_sekarang

from .models import TeacherMaster

HONORIFIC = re.compile(r"^(mr|mrs|ms|miss|bu|pak|ibu|bapak|kak|teacher)\.?\s+", re.I)
TEACHER_STATUSES = ["ACTIVE", "INACTIVE"]
EDITABLE = ("name", "phone", "email", "spec", "emp_type", "status", "join")


def teacher_key(name):
    """Kunci pencocokan nama guru: tanpa sapaan (Mr./Ms./Bu/Pak), huruf kecil, spasi rapat."""
    text = " ".join(str(name or "").replace(".", ". ").split())
    while True:
        new = HONORIFIC.sub("", text)
        if new == text:
            break
        text = new
    return fold(" ".join(text.replace(".", " ").split()))


def find_by_key(branch, name):
    key = teacher_key(name)
    return next((t for t in TeacherMaster.objects.for_branch(branch) if teacher_key(t.name) == key), None) if key else None


@transaction.atomic
def create_teacher(branch, user, *, name, phone="", email="", spec="", emp_type="", status="ACTIVE", join=None):
    name = " ".join(str(name or "").split())
    if not name:
        raise ValidationError("Nama guru wajib diisi.")
    if status not in TEACHER_STATUSES:
        raise ValidationError("Status guru: ACTIVE atau INACTIVE.")
    if find_by_key(branch, name) is not None:
        raise ValidationError(f"Guru {name} sudah ada di daftar guru.")
    tid = next_id(TeacherMaster, "tid", "TCH-APP-", 3, branch)
    t = TeacherMaster.objects.create(branch=branch, row_no=next_row_no(TeacherMaster, branch), tid=tid, name=name, phone=phone, email=email,
                                     spec=spec, emp_type=emp_type, status=status, join=join, unit=branch.unit_id, sources="APLIKASI")
    audit.log(branch=branch, user=user, action="CREATE", entity="TEACHER_MASTER", entity_id=tid, field="Guru baru", new=name)
    return t


@transaction.atomic
def update_teacher(branch, user, tid, **fields):
    t = TeacherMaster.objects.for_branch(branch).filter(tid=tid).first()
    if t is None:
        raise ValidationError(f"Guru {tid} tidak ada di cabang ini.")
    unknown = set(fields) - set(EDITABLE)
    if unknown:
        raise ValidationError(f"Kolom {', '.join(sorted(unknown))} tidak bisa diubah di sini.")
    if "status" in fields and fields["status"] not in TEACHER_STATUSES:
        raise ValidationError("Status guru: ACTIVE atau INACTIVE.")
    if "name" in fields:
        other = find_by_key(branch, fields["name"])
        if other is not None and other.pk != t.pk:
            raise ValidationError(f"Guru {fields['name']} sudah ada di daftar guru.")
    return apply_changes(branch, user, t, "TEACHER_MASTER", tid, fields)


def teacher_rows(branch, today):
    """Ringkasan per guru: murid aktif, kelas, slot jadwal, sesi bulan ini."""
    from classes.models import ClassSchedule, Sesi
    from students.services import dipakai

    data = BranchData(branch, today)
    st = semua_status_sekarang(data)
    aktif, kelas, slots, sesi = {}, {}, {}, {}
    for s in data.students:
        if s.std and fold(st.get(fold(s.std))) == "active":
            k = teacher_key(dipakai(s)["guru"])
            aktif[k] = aktif.get(k, 0) + 1
    for c in data.classes:
        if c.guru and (c.end is None or c.end >= today.replace(day=1)):
            k = teacher_key(c.guru)
            kelas[k] = kelas.get(k, 0) + 1
    for sc in ClassSchedule.objects.for_branch(branch).only("teacher", "eff_until"):
        k = teacher_key(sc.teacher)
        slots[k] = slots.get(k, 0) + 1
    month = f"{today:%Y-%m}"
    for ses in Sesi.objects.for_branch(branch).filter(per=month).only("guru", "status"):
        if fold(ses.status) in ("realized", "make-up"):
            k = teacher_key(ses.guru)
            sesi[k] = sesi.get(k, 0) + 1
    rows = []
    for t in TeacherMaster.objects.for_branch(branch).order_by("name"):
        k = teacher_key(t.name)
        rows.append({"t": t, "key": k, "aktif": aktif.get(k, 0), "kelas": kelas.get(k, 0), "slot": slots.get(k, 0),
                     "sesi": sesi.get(k, 0), "first": as_date(t.first), "last": as_date(t.last)})
    return rows
