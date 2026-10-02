from django.shortcuts import render
from django.utils.cache import patch_vary_headers

from core.capabilities import Cap
from core.decorators import require_cap

from .calc.beranda import cari_murid
from .pages import branch_data, laporan_context


@require_cap(Cap.VIEW)
def cari(request):
    q = request.GET.get("q", "")[:60]
    return render(request, "dashboards/_cari_hasil.html", {"rows": cari_murid(branch_data(request), q), "q": q.strip()})


@require_cap(Cap.VIEW)
def laporan(request):
    partial = request.headers.get("HX-Request") == "true" and request.headers.get("HX-History-Restore-Request") != "true"
    response = render(request, "dashboards/_laporan_body.html" if partial else "dashboards/laporan.html", laporan_context(request))
    patch_vary_headers(response, ["HX-Request"])
    return response
