"""Menu samping: hanya halaman yang sudah ada (URL terdaftar) dan boleh dibuka peran pengguna di cabang aktif."""
from django.urls import NoReverseMatch, reverse

from .capabilities import Cap

NAV = (
    (None, (("Beranda", "core:home", Cap.VIEW, "home"),)),
    ("Admin", (("Impor Data", "importer:upload", Cap.BRANCH_ADMIN, "upload"),
               ("Pengguna & Akses", "accounts:users", Cap.BRANCH_ADMIN, "users"),
               ("Cabang", "branches:list", Cap.MANAGE_ALL, "building"))),
)


def nav_for(request):
    caps = getattr(request, "caps", frozenset())
    if getattr(getattr(request, "user", None), "is_super_admin", False):
        caps = caps | {Cap.MANAGE_ALL}                # menu semua cabang juga tampil tanpa cabang aktif
    groups = []
    for label, items in NAV:
        shown = []
        for text, url_name, cap, icon in items:
            if cap not in caps:
                continue
            try:
                href = reverse(url_name)
            except NoReverseMatch:
                continue
            active = request.path == href if href == "/" else request.path.startswith(href)
            shown.append({"label": text, "href": href, "icon": icon, "active": active})
        if shown:
            groups.append({"label": label, "items": shown})
    return groups
