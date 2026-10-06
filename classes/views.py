"""Halaman kelas, sesi & kehadiran, dan Jadwal Saya (guru)."""
import datetime

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.views.decorators.http import require_POST

from core.permissions import has_perm, require_perm
from core.ui import paginate, sort_key
from dashboards.calc.base import BranchData, as_date, fold
from dashboards.calc.kelas import daftar_kelas
from dashboards.calc.status import kode_dipakai, semua_status_sekarang
from students import services as student_services
from students.forms import teacher_choices
from students.views import _form_errors

from . import calendar, services
from .forms import AddMemberForm, AssignTeacherForm, ClassCreateForm, ClassEditForm, GenerateForm, SlotForm
from .models import ClassMaster, ClassMembers, ClassSchedule, Kehadiran, Sesi

CLASS_SORTS = {"kode": "kode", "aktif": "aktif", "kursi": "kursi", "guru": "guru"}


def _class_or_404(request, code):
    c = ClassMaster.objects.for_branch(request.branch).filter(code__iexact=code).first()
    if c is None:
        raise Http404("Kelas tidak ditemukan di cabang ini.")
    return c


@require_perm("class.view")
def class_list(request):
    data = BranchData(request.branch, timezone.localdate())
    g = request.GET
    f = {"q": g.get("q", "")[:40], "status": g.get("status", "aktif"), "tipe": g.get("tipe", ""), "guru": g.get("guru", "")}
    view = "tabel" if g.get("tampilan") == "tabel" else "kartu"
    schedule = services.schedule_summary(request.branch, data.today)
    rows = []
    for k in daftar_kelas(data):
        c = k.row
        if not c.code:
            continue
        if f["q"] and fold(f["q"]) not in fold(c.code):
            continue
        ended = c.end is not None and c.end < data.bulan_ini
        if f["status"] == "aktif" and (k.status_kelas == "INACTIVE" or (k.status_kelas == "UNKNOWN" and ended)):
            continue                                       # bawaan: aktif, cuti, dan kelas baru yang belum berisi murid
        if f["status"] not in ("aktif", "semua") and k.status_kelas != f["status"]:
            continue
        if f["tipe"] and fold(c.tipe) != fold(f["tipe"]) or f["guru"] and fold(c.guru) != fold(f["guru"]):
            continue
        rows.append({"k": k, "kode": c.code, "aktif": k.aktif, "kursi": k.kursi_kosong, "guru": c.guru or "",
                     "slots": schedule.get(fold(c.code), [])})
    key, desc = sort_key(request, CLASS_SORTS, "kode")
    rows.sort(key=lambda r: (r[CLASS_SORTS[key]], r["kode"]), reverse=desc)
    gurus = sorted({k.row.guru for k in daftar_kelas(data) if k.row.guru}, key=fold)
    summary = {"aktif": sum(1 for k in daftar_kelas(data) if k.status_kelas == "ACTIVE"),
               "kursi": sum(k.kursi_kosong for k in daftar_kelas(data)),
               "penuh": sum(1 for k in daftar_kelas(data) if k.status_kapasitas == "FULL"),
               "melebihi": sum(1 for k in daftar_kelas(data) if k.status_kapasitas == "OVER CAPACITY")}
    return render(request, "classes/list.html", {
        "page": paginate(request, rows, per_page=24 if view == "kartu" else 25), "f": f, "found": len(rows), "gurus": gurus,
        "tipes": list(services.TYPE_LETTER), "view": view,
        "summary": summary, "crumbs": [("Beranda", reverse("core:home")), ("Kelas", None)]})


@require_perm("class.view")
def class_detail(request, code):
    c = _class_or_404(request, code)
    today = timezone.localdate()
    data = BranchData(request.branch, today)
    k = next((x for x in daftar_kelas(data) if x.row.pk == c.pk), None)
    st = semua_status_sekarang(data)
    members = [{"s": s, "status": st.get(fold(s.std), "")} for s in data.students
               if s.std and fold(kode_dipakai(s)) == fold(c.code) and st.get(fold(s.std)) in ("ACTIVE", "ON LEAVE", "PENDING")]
    members.sort(key=lambda m: (m["status"] != "ACTIVE", fold(m["s"].nama)))
    history = ClassMembers.objects.for_branch(request.branch).filter(code__iexact=c.code).exclude(status="CURRENT").order_by("-end", "-row_no")[:50]
    slots = ClassSchedule.objects.for_branch(request.branch).filter(code__iexact=c.code).order_by("row_no")
    upcoming = Sesi.objects.for_branch(request.branch).filter(kode__iexact=c.code, tgl__gte=today).order_by("tgl", "mulai")[:8]
    recent = Sesi.objects.for_branch(request.branch).filter(kode__iexact=c.code, tgl__lt=today).order_by("-tgl", "-mulai")[:8]
    can_over = has_perm(request, "class.over_capacity")
    return render(request, "classes/detail.html", {
        "c": c, "k": k, "members": members, "history": history, "slots": slots, "upcoming": upcoming, "recent": recent,
        "rate": services.attendance_rate(request.branch, kode=c.code), "ended": c.end is not None and c.end <= today,
        "teacher_form": AssignTeacherForm(branch=request.branch, initial={"guru": c.guru}),
        "member_form": AddMemberForm(branch=request.branch, can_over_capacity=can_over),
        "slot_form": SlotForm(branch=request.branch), "today": today,
        "crumbs": [("Kelas", reverse("classes:list")), (c.code, None)]})


@require_perm("class.manage")
def class_create(request):
    form = ClassCreateForm(request.POST or None, branch=request.branch)
    if request.method == "POST" and form.is_valid():
        try:
            c = services.create_class(request.branch, request.user, **form.cleaned_data)
        except ValidationError as exc:
            _form_errors(form, exc)
        else:
            messages.success(request, f"Kelas {c.code} dibuat.")
            return redirect("classes:detail", code=c.code)
    return render(request, "students/form.html", {"form": form, "title": "Kelas baru", "icon": "school", "submit": "Simpan kelas",
                                                  "crumbs": [("Kelas", reverse("classes:list")), ("Baru", None)]})


@require_perm("class.manage")
def class_edit(request, code):
    c = _class_or_404(request, code)
    initial = {"program": c.program, "level": c.level, "mode": c.mode, "bahasa": c.bahasa, "start": c.start}
    form = ClassEditForm(request.POST or None, branch=request.branch, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            services.update_class(request.branch, request.user, c.code, **form.cleaned_data)
        except ValidationError as exc:
            _form_errors(form, exc)
        else:
            messages.success(request, f"Kelas {c.code} diperbarui.")
            return redirect("classes:detail", code=c.code)
    return render(request, "students/form.html", {"form": form, "title": f"Ubah kelas {c.code}", "icon": "edit", "submit": "Simpan",
                                                  "crumbs": [("Kelas", reverse("classes:list")), (c.code, reverse("classes:detail", args=[c.code])), ("Ubah", None)]})


def _post_action(request, code, form_class, run, ok, **form_kwargs):
    c = _class_or_404(request, code)
    form = form_class(request.POST, branch=request.branch, **form_kwargs)
    if not form.is_valid():
        messages.error(request, "; ".join(f"{form.fields[k].label if k in form.fields else ''} {' '.join(v)}".strip() for k, v in form.errors.items()))
    else:
        try:
            run(c, form.cleaned_data)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            messages.success(request, ok)
    return redirect("classes:detail", code=c.code)


@require_POST
@require_perm("class.manage")
def assign_teacher(request, code):
    return _post_action(request, code, AssignTeacherForm,
                        lambda c, d: services.assign_teacher(request.branch, request.user, c.code, guru=d["guru"]),
                        "Guru kelas diganti; murid aktif kelas ini ikut guru baru.")


@require_POST
@require_perm("class.manage")
def add_member(request, code):
    return _post_action(request, code, AddMemberForm,
                        lambda c, d: student_services.change_class(request.branch, request.user, d["std"].strip(), kode=c.code,
                                                                   tanggal=d["tanggal"], allow_over_capacity=d.get("allow_over_capacity", False)),
                        "Murid dimasukkan ke kelas.", can_over_capacity=has_perm(request, "class.over_capacity"))


@require_POST
@require_perm("class.manage")
def add_slot(request, code):
    return _post_action(request, code, SlotForm,
                        lambda c, d: services.add_slot(request.branch, request.user, c.code, **d),
                        "Slot jadwal ditambahkan. Sesi dibuat lewat 'Buat sesi dari jadwal' atau BULAN BARU.")


@require_POST
@require_perm("class.manage")
def end_slot(request, sid):
    slot = ClassSchedule.objects.for_branch(request.branch).filter(sid=sid).first()
    if slot is None:
        raise Http404
    try:
        until = datetime.date.fromisoformat(request.POST.get("until", ""))
        services.end_slot(request.branch, request.user, sid, until=until)
    except (ValueError, ValidationError) as exc:
        messages.error(request, " ".join(getattr(exc, "messages", ["Tanggal akhir tidak sah."])))
    else:
        messages.success(request, f"Slot {sid} berakhir {date_format(until, 'j M Y')}.")
    return redirect("classes:detail", code=slot.code) if slot.code else redirect("classes:list")


@require_POST
@require_perm("class.manage")
def close_class(request, code):
    c = _class_or_404(request, code)
    try:
        services.close_class(request.branch, request.user, c.code, end=timezone.localdate())
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(request, f"Kelas {c.code} ditutup.")
    return redirect("classes:detail", code=c.code)


# ------------------------------------------------------------------ sesi & kehadiran

WEEK_LANES = 2                         # kolom hari di tampilan minggu sempit: 1 sesi + penanda "+N" per gugus bersamaan
CAL_VIEWS = {"hari": "Hari", "minggu": "Minggu", "bulan": "Bulan", "tertunda": "Belum dikonfirmasi"}


def _anchor(request):
    """Tanggal acuan kalender: ?tanggal= (atau ?minggu= lama), selain itu hari ini."""
    for key in ("tanggal", "minggu"):
        try:
            return datetime.date.fromisoformat(request.GET.get(key, ""))
        except ValueError:
            continue
    return timezone.localdate()


@require_perm("session.view")
def session_list(request):
    """Kalender sesi: tampilan hari / minggu / bulan, dan daftar sesi lampau yang belum dikonfirmasi."""
    now = timezone.localtime()
    today = now.date()
    g = request.GET
    view = g.get("tampilan", "minggu") if g.get("tampilan") in CAL_VIEWS else "minggu"
    anchor = _anchor(request)
    if view == "hari":
        start = end = anchor
        prev, nxt = anchor - datetime.timedelta(days=1), anchor + datetime.timedelta(days=1)
    elif view == "bulan":
        start, end = calendar.month_bounds(anchor)
        prev, nxt = calendar.shift_month(anchor, -1), calendar.shift_month(anchor, 1)
    else:
        start = anchor - datetime.timedelta(days=anchor.weekday())
        end = start + datetime.timedelta(days=6)
        prev, nxt = start - datetime.timedelta(days=7), start + datetime.timedelta(days=7)
    f = {"guru": g.get("guru", ""), "kode": g.get("kode", ""), "status": g.get("status", "")}
    qs = Sesi.objects.for_branch(request.branch)
    if view == "tertunda":
        qs = qs.filter(status="SCHEDULED", tgl__lt=today).order_by("-tgl", "mulai", "sid")
    else:
        qs = qs.filter(tgl__range=(start, end)).order_by("tgl", "mulai", "sid")
    if f["status"] and view != "tertunda":
        qs = qs.filter(status=f["status"])
    if f["kode"]:
        qs = qs.filter(kode__iexact=f["kode"])
    rows = [s for s in qs if not f["guru"] or services.teacher_key(s.guru) == services.teacher_key(f["guru"])]
    att = {}
    for r in Kehadiran.objects.filter(branch=request.branch, sid__in=[s.sid for s in rows]):
        a = att.setdefault(r.sid, [0, 0])
        a[0] += 1
        a[1] += r.status in Kehadiran.PRESENT

    def item(s):
        late = s.status == "SCHEDULED" and (as_date(s.tgl) < today or (as_date(s.tgl) == today and s.selesai and s.selesai <= now.time()))
        return {"s": s, "att": att.get(s.sid), "type": calendar.session_type(s), "late": late}

    by_day = calendar.group_by_day(rows)
    lo, hi = calendar.hour_range(rows)
    days, weeks = [], []
    if view in ("hari", "minggu"):
        n = 1 if view == "hari" else 7
        for i in range(n):
            d = start + datetime.timedelta(days=i)
            items = [item(s) for s in by_day.get(d, [])]
            day_url = f"{reverse('classes:sessions')}?tampilan=hari&tanggal={d:%Y-%m-%d}"
            blocks, untimed = calendar.lay_out_day(items, lo, max_lanes=WEEK_LANES if view == "minggu" else None, day=d, day_url=day_url)
            days.append({"date": d, "name": services.DAYS[d.weekday()], "items": items, "blocks": blocks, "untimed": untimed,
                         "is_today": d == today, "now": calendar.now_offset(d, now, lo, hi)})
    elif view == "bulan":
        weeks = calendar.month_weeks(anchor, {d: [item(s) for s in v] for d, v in by_day.items()}, today)
    agenda = [{"date": d, "is_today": d == today, "items": [item(s) for s in v]} for d, v in sorted(by_day.items(), reverse=view == "tertunda")]
    pending = Sesi.objects.for_branch(request.branch).filter(status="SCHEDULED", tgl__lt=today).count()
    keep = {k: v for k, v in f.items() if v}
    return render(request, "classes/sessions.html", {
        "view": view, "views": CAL_VIEWS, "anchor": anchor, "start": start, "end": end, "prev": prev, "next": nxt, "today": today,
        "keep": keep, "days": days, "weeks": weeks, "agenda": agenda, "total": len(rows),
        "hours": [{"h": h, "top": (h - lo) * calendar.HOUR_PX} for h in range(lo, hi + 1)], "grid_h": (hi - lo) * calendar.HOUR_PX,
        "f": f, "statuses": services.SESSION_STATUSES, "pending": pending,
        "monday": start, "sunday": end,
        "gurus": sorted({s.guru for s in Sesi.objects.for_branch(request.branch).only("guru") if s.guru}, key=fold),
        "gen_form": GenerateForm(branch=request.branch, initial={"start": start, "end": end}),
        "crumbs": [("Beranda", reverse("core:home")), ("Sesi & Kehadiran", None)]})


@require_POST
@require_perm("session.manage")
def generate(request):
    form = GenerateForm(request.POST, branch=request.branch)
    if form.is_valid():
        n = services.generate_sessions(request.branch, request.user, form.cleaned_data["start"], form.cleaned_data["end"])
        messages.success(request, f"{n} sesi dibuat dari jadwal resmi (yang sudah ada tidak digandakan).")
        return redirect(reverse("classes:sessions") + f"?minggu={form.cleaned_data['start']:%Y-%m-%d}")
    messages.error(request, " ".join(e for errs in form.errors.values() for e in errs))
    return redirect("classes:sessions")


def session_detail(request, sid):
    """Sesi: staf dengan session.view/manage, atau guru untuk sesi miliknya sendiri."""
    if not request.user.is_authenticated:
        return redirect(f"{reverse('accounts:login')}?next={request.path}")
    if request.branch is None:
        return redirect("core:home")
    ses = Sesi.objects.for_branch(request.branch).filter(sid=sid).first()
    if ses is None:
        raise Http404("Sesi tidak ditemukan di cabang ini.")
    staff_view, staff_manage = has_perm(request, "session.view"), has_perm(request, "session.manage")
    own = has_perm(request, "session.own") and services.is_own_session(request.branch, request.user, ses)
    if not (staff_view or own):
        return render(request, "core/forbidden.html", status=403)
    today = timezone.localdate()
    members = services.session_members(request.branch, ses, today)
    current = {r.std: r.status for r in Kehadiran.objects.filter(branch=request.branch, sid=sid)}
    can_record = staff_manage or own
    if request.method == "POST":
        if not can_record:
            return render(request, "core/forbidden.html", status=403)
        attendance = {m["std"]: request.POST[f"att_{m['std']}"] for m in members if request.POST.get(f"att_{m['std']}")}
        try:
            services.record_session(request.branch, request.user, sid, status=request.POST.get("status", "REALIZED"),
                                    attendance=attendance, catatan=request.POST.get("catatan", ""),
                                    guru_pengganti=request.POST.get("guru_pengganti", "") if staff_manage else "",
                                    own_only=not staff_manage)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            messages.success(request, f"Sesi {ses.kode or ses.kelas} {date_format(as_date(ses.tgl), 'j M')} tersimpan.")
            return redirect("classes:session", sid=sid)
    back = reverse("classes:my_sessions") if not staff_view else reverse("classes:sessions") + f"?minggu={as_date(ses.tgl):%Y-%m-%d}"
    return render(request, "classes/session_detail.html", {
        "ses": ses, "members": [{**m, "status": current.get(m["std"], "")} for m in members], "choices": Kehadiran.STATUS,
        "statuses": services.SESSION_STATUSES, "can_record": can_record, "staff_manage": staff_manage,
        "teachers": teacher_choices(request.branch)[1:] if staff_manage else [],
        "closed": student_services.period_status(request.branch, as_date(ses.tgl)) == "CLOSED",
        "crumbs": [("Jadwal Saya" if not staff_view else "Sesi & Kehadiran", back), (f"{ses.kode or ses.kelas} · {date_format(as_date(ses.tgl), 'j M Y')}", None)]})


@require_perm("session.own")
def my_sessions(request):
    today = timezone.localdate()
    qs, keys = services.teacher_sessions(request.branch, request.user)
    upcoming = qs.filter(tgl__gte=today, tgl__lte=today + datetime.timedelta(days=14)).order_by("tgl", "mulai")
    pending = qs.filter(tgl__lt=today, status="SCHEDULED").order_by("-tgl", "-mulai")[:20]
    done = qs.filter(tgl__lt=today).exclude(status="SCHEDULED").order_by("-tgl", "-mulai")[:10]
    return render(request, "classes/my_sessions.html", {
        "today_items": [s for s in upcoming if as_date(s.tgl) == today], "upcoming": [s for s in upcoming if as_date(s.tgl) > today],
        "pending": pending, "done": done, "has_name": bool(keys), "today": today,
        "crumbs": [("Jadwal Saya", None)]})
