"""Menu samping (arsitektur informasi Super App): hanya halaman yang sudah ada (URL terdaftar) dan boleh dibuka
pengguna di cabang aktif (izin bernama, core/permissions.py)."""
from django.urls import NoReverseMatch, reverse

from .capabilities import Cap
from .permissions import perms_for_caps

# (judul grup, ((label, url name, izin salah satu, ikon Tabler), ...))
NAV = (
    (None, (("Beranda", "core:home", ("student.view",), "home"),
            ("Pusat Tindakan", "students:action_center", ("student.view",), "checklist"),
            ("Jadwal Saya", "classes:my_sessions", ("session.own",), "calendar-user"))),
    ("Murid", (("Murid", "students:list", ("student.view",), "users"),
               ("Orang Tua", "students:parents", ("parent.view",), "users-group"),
               ("Follow-up", "students:followups", ("student.view",), "phone-call"),
               ("OFF", "students:off_list", ("student.view",), "user-off"))),
    ("Akademik", (("Kelas", "classes:list", ("class.view",), "school"),
                  ("Guru", "masterdata:teachers", ("teacher.view",), "user-star"),
                  ("Sesi & Kehadiran", "classes:sessions", ("session.view",), "calendar-event"),
                  ("Akademik", "students:academic", ("student.view",), "book"))),
    ("Keuangan", (("SPP & Keuangan", "finance:home", ("finance.view",), "cash"),)),
    ("Laporan", (("Laporan Murid & SPP", "dashboards:laporan", ("report.view",), "chart-bar"),
                 ("Pusat Laporan", "dashboards:reports", ("report.view",), "report-analytics"))),
    ("Admin", (("Pengguna & Akses", "accounts:users", ("user.manage",), "users"),
               ("Pengaturan", "branches:settings", ("settings.manage",), "settings"),
               ("Audit Log", "audit:log", ("audit.view",), "history"),
               ("Impor Data", "importer:upload", ("import.run",), "upload"),
               ("Cabang", "branches:list", ("branch.manage",), "building"))),
)


def nav_for(request):
    caps = getattr(request, "caps", frozenset())
    if getattr(getattr(request, "user", None), "is_super_admin", False):
        caps = caps | {Cap.MANAGE_ALL}                # menu semua cabang juga tampil tanpa cabang aktif
    perms = perms_for_caps(caps)
    groups = []
    for label, items in NAV:
        shown = []
        for text, url_name, needs, icon in items:
            if not perms.intersection(needs):
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
