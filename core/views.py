from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from branches.models import Branch

from .branch_context import SESSION_KEY, allowed_branches
from .capabilities import Cap

COUNT_TABLES = (
    ("Murid", "students.StudentMaster"), ("Orang tua", "students.ParentMaster"), ("Riwayat bulanan", "students.DBulan"),
    ("Kejadian Off", "students.StudentOff"), ("Kelas", "classes.ClassMaster"), ("Anggota kelas", "classes.ClassMembers"),
    ("Slot jadwal", "classes.ClassSchedule"), ("Guru", "masterdata.TeacherMaster"), ("Program & level", "masterdata.ProgramMaster"),
    ("Baris buku kas", "finance.BukuKas"), ("Pengeluaran", "finance.BukuKasKeluar"), ("Periode", "finance.Periode"),
    ("Tagihan SPP", "finance.SppTagihan"), ("Issue data", "quality.IssueUnit"), ("Audit log", "audit.AuditLog"),
)


@login_required
def home(request):
    if request.branch is None:
        branches = allowed_branches(request.user)
        if not branches.exists():
            return render(request, "core/no_access.html")
        return render(request, "core/choose_branch.html", {"branches": branches})
    if Cap.VIEW not in request.caps:
        return render(request, "core/no_access.html", {"reason": "role"}, status=403)
    counts = [{"label": label, "count": apps.get_model(model).objects.for_branch(request.branch).count()} for label, model in COUNT_TABLES]
    return render(request, "core/home.html", {"counts": counts})


@login_required
@require_POST
def switch_branch(request):
    try:
        branch = allowed_branches(request.user).get(pk=int(request.POST.get("branch", "")))
    except (ValueError, TypeError, Branch.DoesNotExist):
        return render(request, "core/forbidden.html", status=403)
    request.session[SESSION_KEY] = branch.pk
    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}, request.is_secure()):
        return redirect(nxt)
    return redirect("core:home")
