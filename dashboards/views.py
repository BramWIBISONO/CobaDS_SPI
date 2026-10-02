from django.shortcuts import render

from core.capabilities import Cap
from core.decorators import require_cap

from .calc.beranda import cari_murid
from .pages import branch_data


@require_cap(Cap.VIEW)
def cari(request):
    q = request.GET.get("q", "")[:60]
    return render(request, "dashboards/_cari_hasil.html", {"rows": cari_murid(branch_data(request), q), "q": q.strip()})
