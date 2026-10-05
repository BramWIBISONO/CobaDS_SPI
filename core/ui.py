"""Tabel data terstandar: paginasi dan pengurutan yang aman (hanya kolom yang diizinkan)."""
from django.core.paginator import Paginator

PER_PAGE = 25


def paginate(request, items, per_page=PER_PAGE):
    """Halaman ke-N (angka tidak sah -> 1, terlalu besar -> halaman terakhir)."""
    return Paginator(items, per_page).get_page(request.GET.get("page"))


def sort_key(request, allowed, default):
    """('kolom', menurun?) dari ?sort=kolom / ?sort=-kolom; kolom tak dikenal -> bawaan."""
    raw = (request.GET.get("sort") or "").strip()
    desc = raw.startswith("-")
    key = raw[1:] if desc else raw
    if key not in allowed:
        return default, False
    return key, desc
