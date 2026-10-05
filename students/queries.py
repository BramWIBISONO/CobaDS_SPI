"""Bacaan modul murid (daftar & profil 360°). Hanya membaca; perhitungan memakai paket calc yang sama dengan dasbor."""
import datetime

from audit.models import AuditLog
from classes.models import ClassMembers, Kehadiran, Sesi
from dashboards.calc.base import BranchData, as_date, fold
from dashboards.calc.kas import kas_rows
from dashboards.calc.kelas import daftar_kelas
from dashboards.calc.off import daftar_off
from dashboards.calc.status import semua_status_sekarang, status_sekarang
from finance.models import BuktiBayar, SppTagihan

from .models import AcademicRecord, CatatanMurid, FollowUp, ParentMaster, StatusEvent, StudentOff
from .services import STATUS_LABEL, dipakai, is_open_followup

SORTS = {"nama": "nama", "std": "std", "status": "status", "kelas": "kode", "guru": "guru", "program": "level", "join": "join"}


def student_rows(data):
    st = semua_status_sekarang(data)
    rows = []
    for s in data.students:
        if not s.std:
            continue
        d = dipakai(s)
        rows.append({"std": s.std, "nama": s.nama or "", "status": st.get(fold(s.std), ""), "program": d["program"] or "",
                     "level": d["level"] or "", "kode": d["kode"] or "", "guru": d["guru"] or "", "mode": s.mode or "",
                     "join": s.join, "obj": s})
    return rows


def filter_rows(rows, f):
    q = fold(f.get("q", "")).strip()
    out = []
    for r in rows:
        if q and q not in fold(r["nama"]) and q not in fold(r["std"]):
            continue
        if f.get("status") and r["status"] != f["status"]:
            continue
        for key in ("program", "kode", "guru", "mode"):
            if f.get(key) and fold(r[key]) != fold(f[key]):
                break
        else:
            if f.get("join_from") and (r["join"] is None or r["join"] < f["join_from"]):
                continue
            if f.get("join_to") and (r["join"] is None or r["join"] > f["join_to"]):
                continue
            out.append(r)
    return out


def sort_rows(rows, key, desc):
    field = SORTS.get(key, "nama")
    blank_last = datetime.date.min if field == "join" else ""
    return sorted(rows, key=lambda r: (r[field] is None, r[field] or blank_last, fold(r["nama"])), reverse=desc)


def filter_options(rows):
    def distinct(k):
        return sorted({r[k] for r in rows if r[k]}, key=fold)
    return {"status": [(s, STATUS_LABEL[s]) for s in STATUS_LABEL], "program": distinct("program"), "kode": distinct("kode"),
            "guru": distinct("guru"), "mode": distinct("mode")}


def profile(branch, student, today, can_see_contacts):
    data = BranchData(branch, today)
    std = student.std
    d = dipakai(student)
    status = status_sekarang(data, student)
    parent = ParentMaster.objects.for_branch(branch).filter(pid=student.par).first() if student.par else None
    siblings = []
    if parent is not None:
        siblings = [s for s in data.students if s.par == parent.pid and s.std != std]
    kelas = next((k for k in daftar_kelas(data) if d["kode"] and fold(k.row.code) == fold(d["kode"])), None)
    events = sorted(StatusEvent.objects.for_branch(branch).filter(std=std), key=lambda e: (as_date(e.tgl) or datetime.date.min, e.row_no), reverse=True)
    offs = [o for o in daftar_off(data) if o.row.std == std]
    members = ClassMembers.objects.for_branch(branch).filter(std=std).order_by("-start", "-row_no")
    academics = AcademicRecord.objects.for_branch(branch).filter(std=std).order_by("-tgl", "-row_no")
    followups = list(FollowUp.objects.for_branch(branch).filter(std=std).order_by("-tgl", "-row_no").select_related("ditugaskan"))
    notes = CatatanMurid.objects.filter(branch=branch, std=std).select_related("dibuat_oleh")
    tagihan = SppTagihan.objects.for_branch(branch).filter(std=std).order_by("-per")
    bukti = BuktiBayar.objects.for_branch(branch).filter(std=std).order_by("-tgl", "-row_no")
    kas = []
    for k in kas_rows(data):
        for sid, amount in zip(k.s, k.b):
            if sid and fold(sid) == fold(std) and amount:
                kas.append({"bulan": as_date(k.row.bulan), "tgl": as_date(k.row.tgl), "jenis": k.row.jenis, "nominal": amount,
                            "dihitung": k.dihitung, "ket": k.row.ket, "lid": k.row.lid})
    kas.sort(key=lambda r: (r["tgl"] or datetime.date.min), reverse=True)
    hadir = list(Kehadiran.objects.filter(branch=branch, std=std))
    sesi = {x.sid: x for x in Sesi.objects.for_branch(branch).filter(sid__in=[h.sid for h in hadir])}
    attendance = sorted([{"h": h, "s": sesi.get(h.sid)} for h in hadir], key=lambda r: (as_date(r["s"].tgl) if r["s"] else datetime.date.min),
                        reverse=True)
    n_present = sum(1 for h in hadir if h.status in Kehadiran.PRESENT)
    ids = {std} | {e.eid for e in events} | {f.fid for f in followups} | {o.row.off_id for o in offs} | {a.aid for a in academics}
    ids |= {m.mbr for m in members} | {t.tid for t in tagihan} | {b.bid for b in bukti}
    timeline = AuditLog.objects.for_branch(branch).filter(eid__in=ids).order_by("-ts", "-row_no")[:200]
    return {
        "s": student, "d": d, "status": status, "status_label": STATUS_LABEL.get(status, status), "parent": parent,
        "siblings": siblings, "kelas": kelas, "events": events, "offs": offs, "members": members, "academics": academics,
        "followups": followups, "open_followups": [f for f in followups if is_open_followup(f)], "notes": notes,
        "tagihan": tagihan, "bukti": bukti, "kas": kas[:60], "kas_total": sum(r["nominal"] for r in kas if r["dihitung"] == "YA"),
        "timeline": timeline, "contacts": can_see_contacts,
        "last_academic": academics.first(), "attendance": attendance[:60],
        "attendance_rate": {"total": len(hadir), "hadir": n_present, "pct": round(n_present * 100 / len(hadir)) if hadir else None},
    }
