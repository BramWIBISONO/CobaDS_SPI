"""Merakit konteks halaman dasbor dari paket calc (hanya data cabang aktif permintaan ini)."""
from django.utils import timezone

from .calc.base import BranchData, label
from .calc.beranda import beranda


def branch_data(request):
    return BranchData(request.branch, timezone.localdate())


def beranda_context(request):
    h = beranda(branch_data(request))
    spp_label = f"SPP diterima {label(h['spp_bulan'])} (Rp)" if h["spp_bulan"] else "SPP diterima (Rp)"
    return {"h": h, "spp_label": spp_label}
