from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from classes.services import attendance_rate
from core.permissions import require_perm
from students.services import get_student

from . import certificates, services
from .forms import FinalProjectForm
from .models import LULUS_MIN, RUBRIK, FinalProject

TABS = [("menunggu", "Menunggu persetujuan", FinalProject.DIAJUKAN), ("disetujui", "Disetujui", FinalProject.DISETUJUI),
        ("ditolak", "Ditolak", FinalProject.DITOLAK), ("semua", "Semua", None)]


def _project(request, pk):
    return get_object_or_404(FinalProject, branch=request.branch, pk=pk)


@require_perm("student.view")
def daftar(request):
    qs = FinalProject.objects.filter(branch=request.branch)
    tab = request.GET.get("tab", "menunggu")
    tab = tab if tab in {t[0] for t in TABS} else "menunggu"
    want = dict((k, s) for k, _l, s in TABS)[tab]
    counts = {k: (qs.filter(status=s).count() if s else qs.count()) for k, _l, s in TABS}
    rows = qs.filter(status=want) if want else qs
    return render(request, "akademik/daftar.html", {"rows": rows[:200], "tab": tab, "tabs": [(k, l, counts[k]) for k, l, _s in TABS],
                                                    "crumbs": [("Final Project & Sertifikat", None)]})


@require_perm("project.submit")
def ajukan(request, std):
    try:
        s = get_student(request.branch, std)
    except ValidationError:
        raise Http404("Murid tidak ditemukan di cabang ini")
    level = services.level_dipakai(s)
    form = FinalProjectForm(request.POST or None, initial={"rekomendasi": services.level_berikutnya(request.branch, level)})
    if request.method == "POST" and form.is_valid():
        try:
            p = services.ajukan(request.branch, request.user, std, **form.cleaned_data)
        except ValidationError as e:
            form.add_error(None, e)
        else:
            messages.success(request, f"Final project {p.level} {s.nama} diajukan - menunggu persetujuan Manager / Admin.")
            return redirect("akademik:detail", pk=p.pk)
    t = certificates.template_for(services.kode_level(level))
    return render(request, "akademik/ajukan.html", {
        "s": s, "form": form, "level": level, "template": t, "lulus_min": LULUS_MIN,
        "rubrik": [form[f] for f, _l in RUBRIK],
        "crumbs": [("Murid", reverse("students:list")), (s.nama, reverse("students:detail", args=[std])), ("Final project", None)]})


@require_perm("student.view")
def detail(request, pk):
    p = _project(request, pk)
    return render(request, "akademik/detail.html", {
        "p": p, "template": certificates.template_for(p.kode_level), "lulus_min": LULUS_MIN,
        "crumbs": [("Final Project & Sertifikat", reverse("akademik:list")), (f"{p.nama} · {p.level}", None)]})


@require_POST
@require_perm("project.approve")
def setujui(request, pk):
    try:
        p = services.setujui(request.branch, request.user, pk, naik_level=request.POST.get("naik") == "1")
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))
    else:
        teks = f"Disetujui. Sertifikat {p.cert_no} " + ("dan Student Report dibuat otomatis." if p.cert_png else
                                                        "tercatat - template sertifikat level ini belum tersedia, Student Report sudah dibuat.")
        messages.success(request, teks)
    return redirect("akademik:detail", pk=pk)


@require_POST
@require_perm("project.approve")
def tolak(request, pk):
    try:
        services.tolak(request.branch, request.user, pk, alasan=request.POST.get("alasan", ""))
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))
    else:
        messages.success(request, "Final project ditolak; guru bisa mengajukan ulang setelah perbaikan.")
    return redirect("akademik:detail", pk=pk)


@require_POST
@require_perm("project.approve")
def buat_ulang(request, pk):
    p = _project(request, pk)
    if p.status != FinalProject.DISETUJUI or not certificates.template_for(p.kode_level):
        messages.error(request, "Sertifikat belum bisa dibuat: template level ini belum tersedia.")
    else:
        services.buat_ulang_sertifikat(request.branch, request.user, pk)
        messages.success(request, f"Sertifikat {p.cert_no} dibuat.")
    return redirect("akademik:detail", pk=pk)


@require_perm("student.view")
def sertifikat(request, pk, fmt):
    p = _project(request, pk)
    path = {"jpg": p.cert_png, "pdf": p.cert_pdf, "pratinjau": p.cert_preview}.get(fmt)
    if not path:
        raise Http404("Sertifikat belum ada")
    full = Path(settings.MEDIA_ROOT) / path
    if not full.exists():
        raise Http404("File sertifikat tidak ditemukan di server")
    nama = f"Sertifikat {p.cert_no} {p.nama}.{'jpg' if fmt == 'pratinjau' else fmt}"
    return FileResponse(full.open("rb"), as_attachment=fmt != "pratinjau", filename=nama)


@require_perm("student.view")
def rapor(request, pk):
    p = _project(request, pk)
    if p.status == FinalProject.DITOLAK:
        raise Http404("Final project ditolak - tidak ada Student Report")
    s = get_student(request.branch, p.std)
    perjalanan = FinalProject.objects.filter(branch=request.branch, std=p.std, status=FinalProject.DISETUJUI).order_by("tgl_selesai", "pk")
    par = None
    if s.par:
        from students.models import ParentMaster
        par = ParentMaster.objects.for_branch(request.branch).filter(pid=s.par).first()
    from dashboards.calc.base import BranchData
    from django.utils import timezone
    kop = BranchData(request.branch, timezone.localdate()).setting("nota_kop", request.branch.name)
    return render(request, "akademik/rapor.html", {
        "p": p, "s": s, "par": par, "hadir": attendance_rate(request.branch, std=p.std), "perjalanan": perjalanan, "kop": kop,
        "draft": p.status != FinalProject.DISETUJUI, "lulus_min": LULUS_MIN,
        "crumbs": [("Final Project & Sertifikat", reverse("akademik:list")), (f"{p.nama} · {p.level}", reverse("akademik:detail", args=[p.pk])),
                   ("Student Report", None)]})
