"""Halaman modul murid & follow-up. Setiap aksi: izin dicek di server, data hanya dari cabang aktif, perubahan lewat services."""
import csv
import datetime

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.permissions import has_perm, require_perm
from core.ui import paginate, sort_key
from dashboards.calc.base import BranchData, fold

from . import parents, queries, services
from .forms import (ClassForm, FollowUpForm, FollowUpUpdateForm, NoteForm, ParentForm, ProgramForm, StatusForm, StudentCreateForm,
                    StudentEditForm, TeacherForm, off_categories)
from .models import FollowUp, ParentMaster, StudentMaster

TABS = [("ringkasan", "Ringkasan", "id-badge-2"), ("status", "Status & OFF", "activity"), ("kelas", "Kelas", "school"),
        ("kehadiran", "Kehadiran", "calendar-check"), ("akademik", "Akademik", "book"), ("keuangan", "SPP & Pembayaran", "cash"), ("followup", "Follow-up", "phone-call"),
        ("catatan", "Catatan", "notes"), ("riwayat", "Riwayat", "history")]


def _student_or_404(request, std):
    s = StudentMaster.objects.for_branch(request.branch).filter(std=std).first()
    if s is None:
        raise Http404("Murid tidak ditemukan di cabang ini.")
    return s


def _form_errors(form, exc):
    for msg in exc.messages:
        form.add_error(None, msg)


def _parse_date(value):
    try:
        return datetime.date.fromisoformat(value) if value else None
    except ValueError:
        return None


def _list_filters(request):
    g = request.GET
    return {"q": g.get("q", "")[:80], "status": g.get("status", ""), "program": g.get("program", ""), "kode": g.get("kode", ""),
            "guru": g.get("guru", ""), "mode": g.get("mode", ""), "join_from": _parse_date(g.get("join_from")),
            "join_to": _parse_date(g.get("join_to"))}


@require_perm("student.view")
def student_list(request):
    data = BranchData(request.branch, timezone.localdate())
    all_rows = queries.student_rows(data)
    f = _list_filters(request)
    key, desc = sort_key(request, queries.SORTS, "nama")
    rows = queries.sort_rows(queries.filter_rows(all_rows, f), key, desc)
    page = paginate(request, rows)
    ctx = {"page": page, "f": f, "opsi": queries.filter_options(all_rows), "total": len(all_rows), "found": len(rows),
           "n_filters": sum(1 for k, v in f.items() if k != "q" and v),
           "crumbs": [("Beranda", reverse("core:home")), ("Murid", None)]}
    template = "students/_student_table.html" if request.htmx and not request.htmx.history_restore_request else "students/list.html"
    return render(request, template, ctx)


@require_perm("report.export")
def student_export(request):
    data = BranchData(request.branch, timezone.localdate())
    rows = queries.student_rows(data)
    chosen = set(request.GET.getlist("std"))
    rows = [r for r in rows if r["std"] in chosen] if chosen else queries.filter_rows(rows, _list_filters(request))
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="murid-{request.branch.code}-{timezone.localdate():%Y%m%d}.csv"'
    response.write("﻿")
    w = csv.writer(response)
    w.writerow(["Student ID", "Nama", "Status", "Program", "Level", "Kelas", "Guru", "Mode", "Mulai"])   # tanpa kontak (aturan K2)
    for r in rows:
        w.writerow([r["std"], r["nama"], r["status"], r["program"], r["level"], r["kode"], r["guru"], r["mode"],
                    r["join"].isoformat() if r["join"] else ""])
    return response


@require_POST
@require_perm("followup.manage")
def student_bulk(request):
    chosen = [s for s in request.POST.getlist("std") if s]
    form = FollowUpForm(request.POST, branch=request.branch)
    if not chosen:
        messages.warning(request, "Pilih minimal satu murid (centang di daftar).")
    elif not form.is_valid():
        messages.error(request, "Follow-up massal belum lengkap: " + "; ".join(e for errs in form.errors.values() for e in errs))
    else:
        n = 0
        for std in chosen:
            try:
                services.create_followup(request.branch, request.user, std=std, **{k: form.cleaned_data[k] for k in (
                    "jenis", "aksi", "catatan", "jatuh_tempo", "prioritas", "ditugaskan")})
                n += 1
            except ValidationError as exc:
                messages.error(request, f"{std}: {' '.join(exc.messages)}")
        messages.success(request, f"{n} follow-up dibuat.")
    return redirect(request.POST.get("next") or reverse("students:list"))


@require_perm("student.create")
def student_create(request):
    can_over = has_perm(request, "class.over_capacity")
    form = StudentCreateForm(request.POST or None, branch=request.branch, can_over_capacity=can_over)
    if request.method == "POST" and form.is_valid():
        c = dict(form.cleaned_data)
        try:
            s = services.create_student(request.branch, request.user, **c)
        except ValidationError as exc:
            _form_errors(form, exc)
        else:
            messages.success(request, f"Murid baru tersimpan: {s.std} - {s.nama}.")
            return redirect("students:detail", std=s.std)
    return render(request, "students/form.html", {
        "form": form, "title": "Tambah murid", "icon": "user-plus", "submit": "Simpan murid baru",
        "crumbs": [("Murid", reverse("students:list")), ("Tambah murid", None)]})


@require_perm("student.view")
def student_detail(request, std):
    s = _student_or_404(request, std)
    tab = request.GET.get("tab", "ringkasan")
    if tab not in {t[0] for t in TABS}:
        tab = "ringkasan"
    ctx = queries.profile(request.branch, s, timezone.localdate(), has_perm(request, "student.contacts"))
    ctx.update({"tab": tab, "tabs": TABS, "note_form": NoteForm(),
                "crumbs": [("Murid", reverse("students:list")), (s.nama or s.std, None)]})
    return render(request, "students/detail.html", ctx)


@require_perm("student.edit")
def student_edit(request, std):
    s = _student_or_404(request, std)
    initial = {"nama": s.nama, "lahir": s.lahir, "hp": s.hp, "sekolah": s.sekolah_in, "harga": s.harga_in, "ortu_pid": s.par}
    form = StudentEditForm(request.POST or None, branch=request.branch, initial=initial)
    if not has_perm(request, "student.contacts"):
        del form.fields["hp"]
    if request.method == "POST" and form.is_valid():
        try:
            changed = services.update_student(request.branch, request.user, std, **form.cleaned_data)
        except ValidationError as exc:
            _form_errors(form, exc)
        else:
            messages.success(request, f"{len(changed)} data diubah." if changed else "Tidak ada perubahan.")
            return redirect("students:detail", std=std)
    return render(request, "students/form.html", {
        "form": form, "title": f"Ubah data {s.nama}", "icon": "edit", "submit": "Simpan perubahan", "student": s,
        "crumbs": [("Murid", reverse("students:list")), (s.nama, reverse("students:detail", args=[std])), ("Ubah", None)]})


@require_perm("student.status")
def student_status(request, std):
    s = _student_or_404(request, std)
    form = StatusForm(request.POST or None, branch=request.branch)
    if request.method == "POST" and form.is_valid():
        c = form.cleaned_data
        try:
            ev = services.change_status(request.branch, request.user, std, status=c["status"], tanggal=c["tanggal"], alasan=c["alasan"],
                                        kategori=c["kategori"], kembali=c["kembali"], konfirmasi=c["konfirmasi"], catatan=c["catatan"])
            if c["buat_followup"] and c["status"] in ("OFF", "ON LEAVE"):
                services.create_followup(request.branch, request.user, std=std, jenis="OFF" if c["status"] == "OFF" else "Cuti",
                                         aksi="Hubungi orang tua", catatan=c["alasan"], ditugaskan=request.user,
                                         jatuh_tempo=timezone.localdate() + datetime.timedelta(days=3),
                                         prioritas="TINGGI" if c["status"] == "OFF" else "NORMAL")
        except ValidationError as exc:
            _form_errors(form, exc)
        else:
            messages.success(request, f"Status {s.nama} -> {services.STATUS_LABEL[ev.status]} (efektif {ev.tgl:%d %b %Y}) tersimpan.")
            return redirect(reverse("students:detail", args=[std]) + "?tab=status")
    return render(request, "students/status_form.html", {
        "form": form, "student": s, "now": queries.profile(request.branch, s, timezone.localdate(), False)["status"],
        "categories": off_categories(request.branch),
        "crumbs": [("Murid", reverse("students:list")), (s.nama, reverse("students:detail", args=[std])), ("Ubah status", None)]})


@require_perm("student.edit")
def student_class(request, std):
    s = _student_or_404(request, std)
    can_over = has_perm(request, "class.over_capacity")
    action = request.POST.get("action") if request.method == "POST" else None
    forms_ = {"kelas": ClassForm(request.POST if action == "kelas" else None, branch=request.branch, can_over_capacity=can_over),
              "guru": TeacherForm(request.POST if action == "guru" else None, branch=request.branch),
              "program": ProgramForm(request.POST if action == "program" else None, branch=request.branch)}
    if action in forms_ and forms_[action].is_valid():
        c = forms_[action].cleaned_data
        try:
            if action == "kelas":
                services.change_class(request.branch, request.user, std, kode=c["kode"], tanggal=c["tanggal"],
                                      allow_over_capacity=c.get("allow_over_capacity", False))
            elif action == "guru":
                services.change_teacher(request.branch, request.user, std, guru=c["guru"])
            else:
                services.change_program(request.branch, request.user, std, program=c["program"], level=c["level"])
        except ValidationError as exc:
            _form_errors(forms_[action], exc)
        else:
            messages.success(request, "Perubahan kelas / guru / program tersimpan.")
            return redirect(reverse("students:detail", args=[std]) + "?tab=kelas")
    return render(request, "students/class_form.html", {
        "forms": forms_, "student": s, "d": services.dipakai(s),
        "crumbs": [("Murid", reverse("students:list")), (s.nama, reverse("students:detail", args=[std])), ("Kelas, guru & program", None)]})


@require_POST
@require_perm("student.edit")
def student_note(request, std):
    _student_or_404(request, std)
    try:
        services.add_note(request.branch, request.user, std, request.POST.get("teks", ""))
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(request, "Catatan tersimpan.")
    return redirect(reverse("students:detail", args=[std]) + "?tab=catatan")


# ------------------------------------------------------------------ follow-up (Action Center memakai data yang sama)

def _fu_filters(request):
    g = request.GET
    return {"status": g.get("status", "terbuka"), "prioritas": g.get("prioritas", ""), "milik": g.get("milik", ""),
            "jenis": g.get("jenis", ""), "q": g.get("q", "")[:80]}


@require_perm("student.view")
def followup_list(request):
    today = timezone.localdate()
    f = _fu_filters(request)
    rows = FollowUp.objects.for_branch(request.branch).select_related("ditugaskan")
    if f["prioritas"]:
        rows = rows.filter(prioritas=f["prioritas"])
    if f["jenis"]:
        rows = rows.filter(jenis__iexact=f["jenis"])
    if f["milik"] == "saya":
        rows = rows.filter(ditugaskan=request.user)
    names = {s.std: s.nama for s in StudentMaster.objects.for_branch(request.branch).only("std", "nama")}
    items = []
    for fu in rows:
        is_open = services.is_open_followup(fu)
        if f["status"] == "terbuka" and not is_open or f["status"] == "selesai" and is_open:
            continue
        nama = names.get(fu.std, "")
        if f["q"] and fold(f["q"]) not in fold(nama) and fold(f["q"]) not in fold(fu.fid) and fold(f["q"]) not in fold(fu.std):
            continue
        items.append({"fu": fu, "nama": nama, "bucket": services.due_bucket(fu.next, today) if is_open else "SELESAI", "open": is_open})
    order = {"TERLAMBAT": 0, "HARI INI": 1, "MINGGU INI": 2, "NANTI": 3, "TANPA TANGGAL": 4, "SELESAI": 5}
    prio = {p: i for i, p in enumerate(services.FU_PRIORITIES)}
    items.sort(key=lambda r: (order[r["bucket"]], prio.get(r["fu"].prioritas, 9), r["fu"].next or datetime.date.max))
    page = paginate(request, items)
    counts = {b: sum(1 for r in items if r["bucket"] == b) for b in order}
    counts["LAINNYA"] = counts["NANTI"] + counts["TANPA TANGGAL"]
    return render(request, "students/followup_list.html", {
        "page": page, "f": f, "counts": counts, "priorities": services.FU_PRIORITIES,
        "crumbs": [("Beranda", reverse("core:home")), ("Follow-up", None)]})


@require_perm("followup.manage")
def followup_create(request):
    initial = {"std": request.GET.get("std", ""), "jenis": request.GET.get("jenis", ""), "ditugaskan": request.user.pk}
    form = FollowUpForm(request.POST or None, branch=request.branch, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            fu = services.create_followup(request.branch, request.user, **form.cleaned_data)
        except ValidationError as exc:
            _form_errors(form, exc)
        else:
            messages.success(request, f"Follow-up {fu.fid} dibuat.")
            return redirect("students:followup_detail", fid=fu.fid)
    return render(request, "students/form.html", {
        "form": form, "title": "Follow-up baru", "icon": "phone-plus", "submit": "Simpan follow-up",
        "crumbs": [("Follow-up", reverse("students:followups")), ("Baru", None)]})


@require_perm("student.view")
def followup_detail(request, fid):
    fu = FollowUp.objects.for_branch(request.branch).select_related("ditugaskan").filter(fid=fid).first()
    if fu is None:
        raise Http404("Follow-up tidak ditemukan di cabang ini.")
    initial = {"status": fu.status if fu.status in services.FU_STATUSES else "Terbuka", "aksi": fu.aksi, "jatuh_tempo": fu.next,
               "prioritas": fu.prioritas or "NORMAL", "ditugaskan": fu.ditugaskan_id}
    form = FollowUpUpdateForm(request.POST or None, branch=request.branch, initial=initial)
    if request.method == "POST":
        if not has_perm(request, "followup.manage"):
            return render(request, "core/forbidden.html", status=403)
        if form.is_valid():
            c = form.cleaned_data
            try:
                services.update_followup(request.branch, request.user, fid, status=c["status"], catatan=c["catatan"], aksi=c["aksi"],
                                         jatuh_tempo=c["jatuh_tempo"], prioritas=c["prioritas"], ditugaskan=c["ditugaskan"])
            except ValidationError as exc:
                _form_errors(form, exc)
            else:
                messages.success(request, f"Follow-up {fid} diperbarui.")
                return redirect("students:followup_detail", fid=fid)
    student = StudentMaster.objects.for_branch(request.branch).filter(std=fu.std).first() if fu.std else None
    return render(request, "students/followup_detail.html", {
        "fu": fu, "form": form, "student": student, "open": services.is_open_followup(fu),
        "bucket": services.due_bucket(fu.next, timezone.localdate()),
        "crumbs": [("Follow-up", reverse("students:followups")), (fu.fid, None)]})


# ------------------------------------------------------------------ orang tua

def _parent_or_404(request, pid):
    p = ParentMaster.objects.for_branch(request.branch).filter(pid=pid).first()
    if p is None:
        raise Http404("Orang tua tidak ditemukan di cabang ini.")
    return p


@require_perm("parent.view")
def parent_list(request):
    q = request.GET.get("q", "")[:80]
    rows = parents.parent_rows(request.branch, q, has_perm(request, "student.contacts"))
    return render(request, "students/parent_list.html", {
        "page": paginate(request, rows), "q": q, "found": len(rows),
        "crumbs": [("Beranda", reverse("core:home")), ("Orang Tua", None)]})


@require_perm("parent.view")
def parent_detail(request, pid):
    p = _parent_or_404(request, pid)
    data = BranchData(request.branch, timezone.localdate())
    rows = [r for r in queries.student_rows(data) if r["obj"].par == p.pid]
    stds = [r["std"] for r in rows]
    followups = FollowUp.objects.for_branch(request.branch).filter(std__in=stds).order_by("-tgl", "-row_no")[:20]
    return render(request, "students/parent_detail.html", {
        "p": p, "children": rows, "followups": followups, "contacts": has_perm(request, "student.contacts"),
        "communications": [line for line in (p.catatan or "").splitlines() if line.strip()][::-1],
        "crumbs": [("Orang Tua", reverse("students:parents")), (p.nama or p.pid, None)]})


@require_perm("parent.edit")
def parent_create(request):
    form = ParentForm(request.POST or None, branch=request.branch)
    if request.method == "POST" and form.is_valid():
        try:
            p = parents.create_parent(request.branch, request.user, **form.cleaned_data)
        except ValidationError as exc:
            _form_errors(form, exc)
        else:
            messages.success(request, f"Orang tua {p.pid} - {p.nama} tersimpan.")
            return redirect("students:parent_detail", pid=p.pid)
    return render(request, "students/form.html", {
        "form": form, "title": "Tambah orang tua / wali", "icon": "user-plus", "submit": "Simpan",
        "crumbs": [("Orang Tua", reverse("students:parents")), ("Tambah", None)]})


@require_perm("parent.edit")
def parent_edit(request, pid):
    p = _parent_or_404(request, pid)
    contacts = has_perm(request, "student.contacts")
    initial = {name: getattr(p, name) for name in parents.EDITABLE}
    form = ParentForm(request.POST or None, branch=request.branch, initial=initial, can_see_contacts=contacts)
    if request.method == "POST" and form.is_valid():
        try:
            changed = parents.update_parent(request.branch, request.user, pid, **form.cleaned_data)
        except ValidationError as exc:
            _form_errors(form, exc)
        else:
            messages.success(request, f"{len(changed)} data orang tua diubah." if changed else "Tidak ada perubahan.")
            return redirect("students:parent_detail", pid=pid)
    return render(request, "students/form.html", {
        "form": form, "title": f"Ubah {p.nama}", "icon": "edit", "submit": "Simpan perubahan",
        "crumbs": [("Orang Tua", reverse("students:parents")), (p.nama, reverse("students:parent_detail", args=[pid])), ("Ubah", None)]})


@require_POST
@require_perm("parent.edit")
def parent_link(request, pid):
    _parent_or_404(request, pid)
    try:
        parents.link_child(request.branch, request.user, pid, request.POST.get("std", "").strip())
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(request, "Anak dihubungkan ke orang tua ini.")
    return redirect("students:parent_detail", pid=pid)


@require_POST
@require_perm("parent.edit")
def parent_note(request, pid):
    _parent_or_404(request, pid)
    try:
        parents.add_communication(request.branch, request.user, pid, request.POST.get("teks", ""))
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(request, "Catatan komunikasi tersimpan.")
    return redirect("students:parent_detail", pid=pid)
