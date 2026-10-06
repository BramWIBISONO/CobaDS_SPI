"""Beranda = Command Center: apa yang perlu dikerjakan sekarang, lalu kondisi hari ini, angka kunci, akademik, keuangan, aktivitas.
Hanya membaca. Angka situasi tetap dari calc Wave 1 (sama dengan HOME Excel); bagian baru memakai service modul masing-masing.
Setiap bagian hanya dirakit bila pengguna boleh membuka modulnya."""
import datetime
from collections import Counter

from django.urls import reverse
from django.utils import timezone

from .calc.base import fold, label, short_label
from .calc.kas import bulanan, kas_terakhir
from .calc.kelas import daftar_kelas, ringkasan_kelas
from .calc.status import semua_status_sekarang

ACTIVITY_LIMIT = 8
SCHEDULE_LIMIT = 8
ATTENDANCE_DAYS = 30
FINANCE_MONTHS = 6

ACTION_WORDS = {"CREATE": "membuat", "UPDATE": "mengubah", "IMPORT": "mengimpor", "DELETE": "menghapus", "ACCESS": "mengatur akses",
                "STATUS": "mengubah", "LOGIN": "masuk", "LOGOUT": "keluar"}
ENTITY = {"STUDENT_MASTER": ("murid", "user"), "MURID": ("murid", "user"), "STATUS_EVENT": ("status murid", "activity"),
          "FOLLOW_UP": ("follow-up", "phone-call"), "SESI": ("sesi", "calendar-event"), "KEHADIRAN": ("kehadiran", "calendar-check"),
          "CLASS_MASTER": ("kelas", "school"), "KELAS": ("kelas", "school"), "CLASS_MEMBERS": ("anggota kelas", "users"),
          "CLASS_SCHEDULE": ("jadwal kelas", "calendar-time"), "PARENT_MASTER": ("orang tua", "users-group"),
          "TEACHER_MASTER": ("guru", "user-star"), "WORKBOOK": ("workbook", "file-spreadsheet"), "PENGGUNA": ("pengguna", "user-shield"),
          "CABANG": ("cabang", "building"), "CATATAN": ("catatan", "notes")}
PRIVATE_ENTITIES = {"PENGGUNA", "CABANG", "SETTINGS"}            # hanya untuk peran dengan izin audit.view


def greeting(now):
    h = now.hour
    return "Selamat pagi" if h < 11 else "Selamat siang" if h < 15 else "Selamat sore" if h < 18 else "Selamat malam"


def _status_counts(data):
    return Counter(fold(v) for v in semua_status_sekarang(data).values())


def _today_sessions(branch, today, now_time):
    from classes.models import Kehadiran, Sesi

    rows = list(Sesi.objects.for_branch(branch).filter(tgl=today).order_by("mulai", "sid"))
    att = Counter()
    present = Counter()
    for k in Kehadiran.objects.filter(branch=branch, sid__in=[s.sid for s in rows]).only("sid", "status"):
        att[k.sid] += 1
        present[k.sid] += k.status in Kehadiran.PRESENT
    items = []
    for s in rows:
        if s.status == "SCHEDULED" and s.mulai and s.selesai and s.mulai <= now_time < s.selesai:
            phase = "now"
        elif s.status == "SCHEDULED" and s.selesai and s.selesai <= now_time:
            phase = "late"                                          # sudah lewat jam selesai, belum dikonfirmasi
        elif s.status == "SCHEDULED":
            phase = "next"
        else:
            phase = "done"
        items.append({"s": s, "phase": phase, "att": att[s.sid], "present": present[s.sid], "type": (s.kode or "X")[:1].upper()})
    return items


def _attendance(branch, today):
    from classes.models import Sesi
    from classes.services import attendance_rate

    since = today - datetime.timedelta(days=ATTENDANCE_DAYS)
    sids = Sesi.objects.for_branch(branch).filter(tgl__gte=since, tgl__lte=today).values_list("sid", flat=True)
    return attendance_rate(branch, sids=sids)


def _followups(branch, today):
    from students.models import FollowUp
    from students.services import due_bucket, is_open_followup

    buckets = Counter()
    for fu in FollowUp.objects.for_branch(branch).only("status", "next"):
        if is_open_followup(fu):
            buckets[due_bucket(fu.next, today)] += 1
    buckets["TERBUKA"] = sum(v for k, v in buckets.items() if k != "TERBUKA")
    return buckets


def _activity(branch, can_audit):
    from audit.models import AuditLog

    qs = AuditLog.objects.for_branch(branch).exclude(ts=None).order_by("-ts")
    if not can_audit:
        qs = qs.exclude(entity__in=PRIVATE_ENTITIES).exclude(action="ACCESS")
    out = []
    for a in qs[:ACTIVITY_LIMIT]:
        noun, icon = ENTITY.get((a.entity or "").upper(), ((a.entity or "data").lower(), "point"))
        url = ""
        if noun == "murid" and (a.eid or "").startswith("STD-"):
            url = reverse("students:detail", args=[a.eid])
        elif noun == "follow-up" and a.eid:
            url = reverse("students:followup_detail", args=[a.eid])
        elif noun == "orang tua" and a.eid:
            url = reverse("students:parent_detail", args=[a.eid])
        elif noun == "sesi":
            url = reverse("classes:sessions")
        out.append({"who": a.user or "sistem", "verb": ACTION_WORDS.get((a.action or "").upper(), (a.action or "").lower()), "noun": noun,
                    "eid": a.eid, "field": a.field, "new": a.new, "ts": a.ts, "icon": icon, "url": url})
    return out


def _classes(data):
    rows = [k for k in daftar_kelas(data) if k.status_kelas == "ACTIVE"]
    seats = sum(k.kapasitas or 0 for k in rows if isinstance(k.kapasitas, (int, float)))
    filled = sum(k.aktif for k in rows if isinstance(k.kapasitas, (int, float)) and k.kapasitas)
    return {**ringkasan_kelas(data), "seats": int(seats), "filled": int(filled)}


def _finance(data):
    kas = kas_terakhir(data)
    months = bulanan(data)[-FINANCE_MONTHS:]
    peak = max((m[1] for m in months), default=0) or 1
    bars = [{"label": short_label(m[0]), "value": m[1], "pct": round(m[1] * 100 / peak)} for m in months]
    trend = None
    if kas and kas["prev_total"]:
        trend = round((kas["total"] - kas["prev_total"]) * 100 / kas["prev_total"], 1)
    return {"kas": kas, "bars": bars, "trend": trend, "bulan": label(kas["bulan"]) if kas else "",
            "prev_bulan": label(kas["prev_bulan"]) if kas and kas["prev_bulan"] else ""}


def command_center(request, data, h, perms):
    """Konteks Command Center. `h` = ringkasan HOME (calc.beranda) yang sudah dihitung."""
    branch = request.branch
    now = timezone.localtime()
    today = now.date()
    sessions = _today_sessions(branch, today, now.time()) if "session.view" in perms else []
    fus = _followups(branch, today) if "student.view" in perms else Counter()
    st = _status_counts(data)
    off_baru, off_masih, off_perlu = h["off_raw"]
    kelas = _classes(data)
    pending_past = 0
    if "session.view" in perms:
        from classes.models import Sesi

        pending_past = Sesi.objects.for_branch(branch).filter(status="SCHEDULED", tgl__lt=today).count()
    late_today = sum(1 for x in sessions if x["phase"] == "late")
    done_today = sum(1 for x in sessions if x["phase"] == "done")

    actions = []

    def add(level, icon, title, detail, count, url, cta):
        actions.append({"level": level, "icon": icon, "title": title, "detail": detail, "count": count, "url": url, "cta": cta})

    sessions_url = reverse("classes:sessions") if "session.view" in perms else ""
    if pending_past:
        add("danger", "calendar-exclamation", "Sesi lampau belum dikonfirmasi", "Realisasi & kehadiran belum dicatat untuk sesi yang sudah lewat",
            pending_past, f"{sessions_url}?tampilan=tertunda", "Konfirmasi sesi")
    if late_today:
        add("warning", "clipboard-check", "Absensi hari ini belum selesai", f"{late_today} dari {len(sessions)} sesi hari ini sudah lewat jam selesai",
            late_today, f"{sessions_url}?tampilan=hari&tanggal={today:%Y-%m-%d}", "Catat kehadiran")
    if "student.view" in perms:
        fu_url = reverse("students:followups")
        if fus["TERLAMBAT"]:
            add("danger", "phone-x", "Follow-up terlambat", "Jatuh tempo sudah lewat - hubungi orang tua / selesaikan tugas",
                fus["TERLAMBAT"], fu_url, "Buka follow-up")
        if fus["HARI INI"]:
            add("warning", "phone-call", "Follow-up jatuh tempo hari ini", "Tugas staf yang harus selesai hari ini", fus["HARI INI"], fu_url, "Kerjakan")
        if off_perlu:
            add("warning", "user-off", "Murid OFF perlu follow-up", f"{off_masih} murid masih OFF · {off_baru} baru OFF bulan ini",
                off_perlu, f"{reverse('students:list')}?status=OFF", "Lihat murid OFF")
        if st["pending"]:
            add("info", "user-question", "Murid berstatus PENDING", "Belum dipastikan aktif - konfirmasi kelas & jadwalnya",
                st["pending"], f"{reverse('students:list')}?status=PENDING", "Tinjau")
    if h["bukti"]:
        add("warning", "receipt", "Pembayaran menunggu verifikasi", "Bukti bayar dari INPUT CENTER · verifikasi di aplikasi dibangun bersama modul Keuangan",
            h["bukti"], reverse("dashboards:laporan"), "Lihat laporan SPP")
    if h["kritis"]:
        add("danger", "alert-octagon", "Masalah kritis terbuka", h["sub_kritis"], h["kritis"], reverse("dashboards:laporan"), "Tinjau")
    if kelas["melebihi"] and "class.view" in perms:
        add("warning", "users-minus", "Kelas melebihi kapasitas", "Pindahkan murid atau naikkan kapasitas kelas", kelas["melebihi"],
            f"{reverse('classes:list')}?sort=kursi", "Lihat kelas")
    order = {"danger": 0, "warning": 1, "info": 2}
    actions.sort(key=lambda a: order[a["level"]])

    first = (getattr(request.user, "display_name", "") or "").split(" ")[0]
    facts = []
    if "session.view" in perms:
        facts.append(f"{len(sessions)} sesi kelas hari ini" if sessions else "tidak ada sesi kelas hari ini")
    if "student.view" in perms:
        facts.append(f"{fus['TERBUKA']} follow-up terbuka")
    facts.append(f"{len(actions)} hal perlu tindakan" if actions else "tidak ada pekerjaan mendesak")

    att = _attendance(branch, today) if "session.view" in perms else None
    kpi = {"sessions_sub": f"{done_today} dikonfirmasi · {late_today} menunggu absensi" if sessions else "tidak ada sesi terjadwal hari ini",
           "att_value": f"{att['pct']}%" if att and att["pct"] is not None else "—",
           "att_sub": (f"hadir {att['hadir']} dari {att['total']} catatan kehadiran" if att and att["pct"] is not None
                       else "belum ada kehadiran tercatat - dicatat saat sesi dikonfirmasi")}
    return {
        "greeting": greeting(now), "first_name": first, "now": now, "facts": facts,
        "actions": actions,
        "today_sessions": sessions[:SCHEDULE_LIMIT], "today_more": max(0, len(sessions) - SCHEDULE_LIMIT), "today_total": len(sessions),
        "today_done": done_today, "today_late": late_today, "sessions_url": sessions_url,
        "attendance": att, "kpi": kpi,
        "status_counts": {"aktif": st["active"], "cuti": st["on leave"], "pending": st["pending"], "off": st["off"]},
        "status_total": st["active"] + st["on leave"] + st["pending"] + st["off"],
        "kelas": kelas,
        "finance": _finance(data) if "finance.view" in perms else None,
        "activity": _activity(branch, "audit.view" in perms),
        "followups": fus,
    }
