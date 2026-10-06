from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from branches.models import Branch
from dashboards.pages import beranda_context

from .branch_context import SESSION_KEY, allowed_branches
from .capabilities import Cap
from .models import Notifikasi
from .notifications import mark_read
from .permissions import perms_for_caps, require_perm
from .search import global_search


@login_required
def home(request):
    if request.branch is None:
        branches = allowed_branches(request.user)
        if not branches.exists():
            return render(request, "core/no_access.html")
        return render(request, "core/choose_branch.html", {"branches": branches})
    if Cap.VIEW not in request.caps:
        if Cap.SESSION_WRITE_OWN in request.caps:
            return redirect("classes:my_sessions")                     # guru: halaman kerjanya = Jadwal Saya
        return render(request, "core/no_access.html", {"reason": "role"}, status=403)
    return render(request, "dashboards/beranda.html", beranda_context(request))


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


@login_required
def notifikasi_list(request):
    items = Notifikasi.objects.filter(user=request.user, branch=request.branch)[:100] if request.branch else []
    return render(request, "core/notifikasi.html", {"items": items})


@login_required
@require_POST
def notifikasi_baca(request, pk):
    n = get_object_or_404(Notifikasi, pk=pk, user=request.user)
    mark_read(n)
    target = n.url if n.url and url_has_allowed_host_and_scheme(n.url, {request.get_host()}, request.is_secure()) else "core:notifikasi"
    return redirect(target)


@login_required
@require_POST
def notifikasi_baca_semua(request):
    Notifikasi.objects.filter(user=request.user, branch=request.branch, read_at__isnull=True).update(read_at=timezone.now())
    return redirect("core:notifikasi")


@login_required
def search(request):
    """Hasil pencarian global (potongan HTMX di bawah kotak cari topbar)."""
    result = global_search(request.branch, perms_for_caps(request.caps), request.GET.get("q", ""))
    return render(request, "core/_search_results.html", result)


@require_perm("settings.manage")
def ui_kit(request):
    """Contoh hidup design system (komponen, status, fondasi visual Keuangan) - acuan untuk modul berikutnya."""
    return render(request, "core/ui_kit.html", {"crumbs": [("Admin", None), ("UI Kit", None)]})
