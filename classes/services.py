"""Layanan kelas, jadwal resmi, sesi, dan kehadiran (Guru & Kelas Baru, Jadwal, Realisasi Pertemuan v4 + kehadiran per murid)."""
import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from branches.models import Membership
from core import audit
from core.ids import next_id, next_row_no
from core.records import apply_changes
from dashboards.calc.base import BranchData, as_date, fold, period_code
from dashboards.calc.status import event_terakhir, kode_dipakai, semua_status_sekarang
from masterdata.services import find_by_key, teacher_key
from students.services import check_program, ensure_open, find_class, find_teacher, period_status

from .models import ClassMaster, ClassSchedule, Kehadiran, Sesi

TYPE_LETTER = {"Focus": "F", "Partner": "P", "Group": "G", "School": "S"}
DAYS = ["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT", "SABTU", "MINGGU"]
SESSION_STATUSES = ["SCHEDULED", "REALIZED", "MAKE-UP", "CANCELLED"]
ATTENDANCE = dict(Kehadiran.STATUS)
SOURCE = "APLIKASI"


def day_name(d):
    return DAYS[d.weekday()]


def _parse_day(value):
    """Tanggal dari kolom teks jadwal (ISO); teks lain (UNKNOWN, kosong) = tidak membatasi."""
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        return None


def slot_valid(slot, d):
    if fold(slot.day).strip() != fold(day_name(d)):
        return False
    start, until = _parse_day(slot.eff_from), _parse_day(slot.eff_until)
    return not (start and d < start) and not (until and d > until)


@transaction.atomic
def create_class(branch, user, *, code, tipe, program="", level="", guru="", mode="", bahasa="", start=None):
    code = str(code or "").strip().upper()
    if not code:
        raise ValidationError("Kode kelas wajib diisi.")
    if tipe not in TYPE_LETTER:
        raise ValidationError("Tipe kelas: Focus, Partner, Group, atau School.")
    if code[0] != TYPE_LETTER[tipe]:
        raise ValidationError(f"Huruf pertama kode menentukan tipe & kapasitas: kode {tipe} harus diawali {TYPE_LETTER[tipe]}.")
    if ClassMaster.objects.for_branch(branch).filter(code__iexact=code).exists():
        raise ValidationError(f"Kode kelas {code} sudah ada.")
    if guru:
        guru = find_teacher(branch, guru).name
    check_program(branch, program, level)
    cid = f"CLS-{code}"
    c = ClassMaster.objects.create(branch=branch, row_no=next_row_no(ClassMaster, branch), class_id=cid, code=code, tipe=tipe,
                                   program=program, level=level, guru=guru, mode=mode, bahasa=bahasa, start=start,
                                   unit=branch.unit_id, sheets=SOURCE)
    audit.log(branch=branch, user=user, action="CREATE", entity="CLASS_MASTER", entity_id=cid, field="Kelas baru", new=f"{code} {tipe} {guru}")
    return c


def get_class(branch, code):
    return find_class(branch, code)


@transaction.atomic
def update_class(branch, user, code, **fields):
    c = get_class(branch, code)
    allowed = {"program", "level", "mode", "bahasa", "start"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValidationError(f"Kolom {', '.join(sorted(unknown))} tidak bisa diubah di sini.")
    if "program" in fields or "level" in fields:
        check_program(branch, fields.get("program", c.program), fields.get("level", c.level))
    return apply_changes(branch, user, c, "CLASS_MASTER", c.class_id, fields)


def active_members(branch, code, today):
    data = BranchData(branch, today)
    st = semua_status_sekarang(data)
    return [s for s in data.students if s.std and fold(kode_dipakai(s)) == fold(code) and fold(st.get(fold(s.std))) == "active"]


@transaction.atomic
def assign_teacher(branch, user, code, *, guru, today=None, follow_members=True):
    today = today or timezone.localdate()
    c = get_class(branch, code)
    name = find_teacher(branch, guru).name
    apply_changes(branch, user, c, "CLASS_MASTER", c.class_id, {"guru": name})
    if follow_members:
        for s in active_members(branch, c.code, today):
            apply_changes(branch, user, s, "STUDENT_MASTER", s.std, {"guru_in": name})
    return c


@transaction.atomic
def close_class(branch, user, code, *, end, today=None):
    today = today or timezone.localdate()
    c = get_class(branch, code)
    n = len(active_members(branch, c.code, today))
    if n:
        raise ValidationError(f"Kelas {c.code} masih punya {n} murid aktif - pindahkan murid dulu.")
    apply_changes(branch, user, c, "CLASS_MASTER", c.class_id, {"end": end})
    return c


@transaction.atomic
def add_slot(branch, user, code, *, day, start, end, room="", teacher="", eff_from=None, mode=""):
    c = get_class(branch, code)
    if day not in DAYS:
        raise ValidationError("Hari tidak dikenal.")
    if start is None or end is None or end <= start:
        raise ValidationError("Jam selesai harus setelah jam mulai.")
    name = find_teacher(branch, teacher).name if teacher else c.guru
    if not name:
        raise ValidationError("Kelas belum punya guru - pilih guru untuk slot ini.")
    for other in ClassSchedule.objects.for_branch(branch).filter(day__iexact=day):
        if teacher_key(other.teacher) != teacher_key(name) or other.start is None or other.end is None:
            continue
        until = _parse_day(other.eff_until)
        if until and eff_from and until < eff_from:
            continue
        if other.start < end and start < other.end:
            raise ValidationError(f"Bentrok dengan jadwal {name} {day} {other.start:%H:%M}-{other.end:%H:%M} ({other.code or other.text or other.sid}).")
    sid = next_id(ClassSchedule, "sid", "SCH-APP-", 6, branch)
    slot = ClassSchedule.objects.create(branch=branch, row_no=next_row_no(ClassSchedule, branch), sid=sid, code=c.code, class_id=c.class_id,
                                        day=day, start=start, end=end, room=room, mode=mode or c.mode, teacher=name,
                                        eff_from=eff_from.isoformat() if eff_from else "", text=f"{c.code} {c.tipe}", flag=SOURCE)
    audit.log(branch=branch, user=user, action="CREATE", entity="CLASS_SCHEDULE", entity_id=sid, field="Slot jadwal",
              new=f"{c.code} {day} {start:%H:%M}-{end:%H:%M} {name}")
    return slot


@transaction.atomic
def end_slot(branch, user, sid, *, until):
    slot = ClassSchedule.objects.for_branch(branch).filter(sid=sid).first()
    if slot is None:
        raise ValidationError(f"Slot {sid} tidak ada di cabang ini.")
    apply_changes(branch, user, slot, "CLASS_SCHEDULE", sid, {"eff_until": until.isoformat()})
    return slot


@transaction.atomic
def generate_sessions(branch, user, start, end):
    """Sesi SCHEDULED dari slot jadwal yang berlaku per tanggal; ID SES-yyyymmdd-<slot> sehingga tidak pernah dobel."""
    slots = list(ClassSchedule.objects.for_branch(branch).exclude(sid=""))
    have = set(Sesi.objects.for_branch(branch).filter(tgl__range=(start, end)).values_list("sid", flat=True))
    rows, d, row = [], start, next_row_no(Sesi, branch)
    while d <= end:
        if period_status(branch, d) == "CLOSED":
            d += datetime.timedelta(days=1)
            continue
        for slot in slots:
            sid = f"SES-{d:%Y%m%d}-{slot.sid}"
            if sid in have or not slot_valid(slot, d):
                continue
            rows.append(Sesi(branch=branch, row_no=row, sid=sid, per=period_code(d), tgl=d, hari=day_name(d), mulai=slot.start,
                             selesai=slot.end, guru=slot.teacher, kode=slot.code, kelas=slot.text or slot.code, ruang=slot.room,
                             slot=slot.sid, status="SCHEDULED", sumber="JADWAL"))
            have.add(sid)
            row += 1
        d += datetime.timedelta(days=1)
    Sesi.objects.bulk_create(rows)
    if rows:
        audit.log(branch=branch, user=user, action="CREATE", entity="SESI", entity_id=f"{start:%Y%m%d}-{end:%Y%m%d}", field="Sesi dari jadwal",
                  new=f"{len(rows)} sesi")
    return len(rows)


def session_members(branch, ses, today):
    """Murid kelas sesi itu yang ACTIVE pada tanggal sesi (status terakhir s/d tanggal itu, lalu status awal)."""
    if not ses.kode:
        return []
    data = BranchData(branch, today)
    d = as_date(ses.tgl) or today
    out = []
    for s in data.students:
        if not s.std or fold(kode_dipakai(s)) != fold(ses.kode):
            continue
        st = event_terakhir(data, s.std, d)
        st = st if st is not None else (s.st_base or "PENDING")
        if fold(st) == "active":
            out.append({"std": s.std, "nama": s.nama, "obj": s})
    return out


def is_own_session(branch, user, ses):
    names = Membership.objects.filter(user=user, branch=branch).values_list("teacher_name", flat=True)
    return any(n and teacher_key(n) == teacher_key(ses.guru) for n in names)


@transaction.atomic
def record_session(branch, user, sid, *, status, attendance, catatan="", guru_pengganti="", own_only=False, today=None):
    """Realisasi pertemuan: status sesi, kehadiran per murid (unik, ubahan diaudit), guru pengganti, konfirmasi."""
    today = today or timezone.localdate()
    ses = Sesi.objects.for_branch(branch).filter(sid=sid).first()
    if ses is None:
        raise ValidationError(f"Sesi {sid} tidak ada di cabang ini.")
    if own_only and not is_own_session(branch, user, ses):
        raise ValidationError("Ini bukan sesi Anda - guru hanya mencatat sesi miliknya.")
    if status not in SESSION_STATUSES:
        raise ValidationError("Status sesi tidak dikenal.")
    ensure_open(branch, as_date(ses.tgl), "Sesi")
    members = {m["std"] for m in session_members(branch, ses, today)}
    for std, st in attendance.items():
        if st not in ATTENDANCE:
            raise ValidationError(f"Status kehadiran {st} tidak dikenal.")
        if std not in members:
            raise ValidationError(f"{std} bukan anggota aktif kelas {ses.kode} pada tanggal sesi.")
    for std, st in attendance.items():
        row = Kehadiran.objects.filter(branch=branch, sid=sid, std=std).first()
        if row is None:
            Kehadiran.objects.create(branch=branch, sid=sid, std=std, status=st, dicatat_oleh=user)
            audit.log(branch=branch, user=user, action="CREATE", entity="KEHADIRAN", entity_id=sid, field=std, new=st)
        elif row.status != st:
            audit.log(branch=branch, user=user, action="UPDATE", entity="KEHADIRAN", entity_id=f"{sid}/{std}", field="Status",
                      old=row.status, new=st)
            row.status, row.dicatat_oleh = st, user
            row.save(update_fields=["status", "dicatat_oleh", "diubah_pada"])
    rows = Kehadiran.objects.filter(branch=branch, sid=sid)
    changes = {"status": status, "konf_oleh": audit.actor_name(user), "konf_pada": timezone.now()}
    if rows.exists():
        names = {s.std: s.nama for s in BranchData(branch, today).students}
        changes["hadir"] = float(sum(1 for r in rows if r.status in Kehadiran.PRESENT))
        changes["absen"] = ", ".join(names.get(r.std, r.std) for r in rows if r.status not in Kehadiran.PRESENT)
    note = catatan.strip()
    if guru_pengganti:
        sub = find_teacher(branch, guru_pengganti).name
        if teacher_key(sub) != teacher_key(ses.guru):
            note = f"guru pengganti untuk {ses.guru}. {note}".strip()
            changes["guru"] = sub
    if note:
        changes["catatan"] = f"{ses.catatan} {note}".strip()
    apply_changes(branch, user, ses, "SESI", sid, changes)
    return ses


def attendance_rate(branch, *, std=None, kode=None, sids=None):
    """Persentase hadir (Hadir + Terlambat) dari kehadiran tercatat."""
    rows = Kehadiran.objects.filter(branch=branch)
    if std:
        rows = rows.filter(std=std)
    if kode:
        rows = rows.filter(sid__in=Sesi.objects.for_branch(branch).filter(kode__iexact=kode).values("sid"))
    if sids is not None:
        rows = rows.filter(sid__in=list(sids))
    total = rows.count()
    hadir = rows.filter(status__in=Kehadiran.PRESENT).count()
    return {"total": total, "hadir": hadir, "pct": round(hadir * 100 / total) if total else None}


def teacher_sessions(branch, user):
    """Sesi milik guru (nama guru di keanggotaan cabang) - untuk halaman Jadwal Saya."""
    keys = {teacher_key(n) for n in Membership.objects.filter(user=user, branch=branch).values_list("teacher_name", flat=True) if n}
    if not keys:
        return Sesi.objects.none(), keys
    ids = [s.pk for s in Sesi.objects.for_branch(branch).only("pk", "guru") if teacher_key(s.guru) in keys]
    return Sesi.objects.filter(pk__in=ids), keys


__all__ = ["create_class", "update_class", "assign_teacher", "close_class", "add_slot", "end_slot", "generate_sessions",
           "session_members", "record_session", "attendance_rate", "teacher_sessions", "find_by_key"]
