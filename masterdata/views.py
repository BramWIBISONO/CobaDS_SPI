"""Halaman guru: daftar (beban kerja), profil (kelas, jadwal, murid, sesi & kehadiran), tambah / ubah."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from classes.models import ClassSchedule, Sesi
from classes.services import attendance_rate
from core.permissions import require_perm
from core.ui import paginate
from dashboards.calc.base import BranchData, fold
from dashboards.calc.status import semua_status_sekarang
from students.services import dipakai
from students.views import _form_errors

from . import services
from .forms import TeacherForm
from .models import TeacherMaster


def _teacher_or_404(request, tid):
    t = TeacherMaster.objects.for_branch(request.branch).filter(tid=tid).first()
    if t is None:
        raise Http404("Guru tidak ditemukan di cabang ini.")
    return t


@require_perm("teacher.view")
def teacher_list(request):
    status = request.GET.get("status", "ACTIVE")
    rows = [r for r in services.teacher_rows(request.branch, timezone.localdate()) if not status or fold(r["t"].status) == fold(status)]
    rows.sort(key=lambda r: (-r["aktif"], fold(r["t"].name)))
    return render(request, "masterdata/teachers.html", {
        "page": paginate(request, rows), "status": status, "found": len(rows), "max_aktif": max((r["aktif"] for r in rows), default=0),
        "crumbs": [("Beranda", reverse("core:home")), ("Guru", None)]})


@require_perm("teacher.view")
def teacher_detail(request, tid):
    t = _teacher_or_404(request, tid)
    today = timezone.localdate()
    key = services.teacher_key(t.name)
    data = BranchData(request.branch, today)
    st = semua_status_sekarang(data)
    classes = [c for c in data.classes if c.code and services.teacher_key(c.guru) == key]
    students = sorted([{"s": s, "d": dipakai(s)} for s in data.students
                       if s.std and fold(st.get(fold(s.std))) == "active" and services.teacher_key(dipakai(s)["guru"]) == key],
                      key=lambda r: fold(r["s"].nama))
    slots = [sc for sc in ClassSchedule.objects.for_branch(request.branch).order_by("row_no") if services.teacher_key(sc.teacher) == key]
    sesi = [s for s in Sesi.objects.for_branch(request.branch).order_by("-tgl", "-mulai")[:400] if services.teacher_key(s.guru) == key]
    month = [s for s in sesi if s.per == f"{today:%Y-%m}"]
    return render(request, "masterdata/teacher_detail.html", {
        "t": t, "classes": classes, "students": students, "slots": slots, "recent": sesi[:15],
        "month_done": sum(1 for s in month if fold(s.status) in ("realized", "make-up")), "month_total": len(month),
        "rate": attendance_rate(request.branch, sids=[s.sid for s in sesi]),
        "crumbs": [("Guru", reverse("masterdata:teachers")), (t.name, None)]})


@require_perm("teacher.manage")
def teacher_create(request):
    form = TeacherForm(request.POST or None, branch=request.branch, initial={"status": "ACTIVE"})
    if request.method == "POST" and form.is_valid():
        try:
            t = services.create_teacher(request.branch, request.user, **form.cleaned_data)
        except ValidationError as exc:
            _form_errors(form, exc)
        else:
            messages.success(request, f"Guru {t.name} ({t.tid}) tersimpan.")
            return redirect("masterdata:teacher", tid=t.tid)
    return render(request, "students/form.html", {"form": form, "title": "Guru baru", "icon": "user-star", "submit": "Simpan guru",
                                                  "crumbs": [("Guru", reverse("masterdata:teachers")), ("Baru", None)]})


@require_perm("teacher.manage")
def teacher_edit(request, tid):
    t = _teacher_or_404(request, tid)
    initial = {name: getattr(t, name) for name in services.EDITABLE}
    form = TeacherForm(request.POST or None, branch=request.branch, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            changed = services.update_teacher(request.branch, request.user, tid, **form.cleaned_data)
        except ValidationError as exc:
            _form_errors(form, exc)
        else:
            messages.success(request, f"{len(changed)} data guru diubah." if changed else "Tidak ada perubahan.")
            return redirect("masterdata:teacher", tid=tid)
    return render(request, "students/form.html", {
        "form": form, "title": f"Ubah {t.name}", "icon": "edit", "submit": "Simpan",
        "crumbs": [("Guru", reverse("masterdata:teachers")), (t.name, reverse("masterdata:teacher", args=[tid])), ("Ubah", None)]})
