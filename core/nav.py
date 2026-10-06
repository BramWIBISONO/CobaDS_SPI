"""Menu samping (arsitektur informasi Super App): hanya halaman yang sudah ada (URL terdaftar) dan boleh dibuka
pengguna di cabang aktif (izin bernama, core/permissions.py)."""
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from .capabilities import Cap
from .permissions import perms_for_caps

# (judul grup, ((label, url name, izin salah satu, ikon Tabler), ...))
NAV = (
    (None, (("Beranda", "core:home", ("student.view",), "home"),
            ("Pusat Tindakan", "students:action_center", ("student.view",), "checklist"),
            ("Jadwal Saya", "classes:my_sessions", ("session.own",), "calendar-user"))),
    ("Management", (("Management Center", "management:center", ("management.view",), "layout-dashboard"),
                    ("Business Health", "management:health", ("management.view",), "heart-rate-monitor"),
                    ("Student Lifecycle", "management:lifecycle", ("management.view",), "timeline"),
                    ("Finance Control", "management:finance", ("management.finance",), "report-money"),
                    ("Nota SPP", "management:nota", ("management.finance",), "receipt"),
                    ("Operational Health", "management:operations", ("management.view",), "activity-heartbeat"),
                    ("Data Health", "management:data", ("management.view",), "database-search"),
                    ("Management Reports", "management:reports", ("management.view",), "file-analytics"))),
    ("Murid", (("Murid", "students:list", ("student.view",), "users"),
               ("Orang Tua", "students:parents", ("parent.view",), "users-group"),
               ("Follow-up", "students:followups", ("student.view",), "phone-call"),
               ("OFF", "students:off_list", ("student.view",), "user-off"))),
    ("Akademik", (("Kelas", "classes:list", ("class.view",), "school"),
                  ("Guru", "masterdata:teachers", ("teacher.view",), "user-star"),
                  ("Sesi & Kehadiran", "classes:sessions", ("session.view",), "calendar-event"),
                  ("Akademik", "students:academic", ("student.view",), "book"),
                  ("Final Project & Sertifikat", "akademik:list", ("student.view",), "certificate"))),
    ("Keuangan", (("SPP & Keuangan", "finance:home", ("finance.view",), "cash"),)),
    ("Laporan", (("Laporan Murid & SPP", "dashboards:laporan", ("report.view",), "chart-bar"),
                 ("Pusat Laporan", "dashboards:reports", ("report.view",), "report-analytics"))),
    ("Admin", (("Pengguna & Akses", "accounts:users", ("user.manage",), "users"),
               ("Pengaturan", "branches:settings", ("settings.manage",), "settings"),
               ("Audit Log", "audit:log", ("audit.view",), "history"),
               ("Impor Data", "importer:upload", ("import.run",), "upload"),
               ("UI Kit", "core:ui_kit", ("settings.manage",), "palette"),
               ("Cabang", "branches:list", ("branch.manage",), "building"))),
)


def nav_badges(request, perms):
    """Angka kecil di menu = pekerjaan yang sudah lewat waktunya (hanya untuk menu yang boleh dibuka; dua query ringan)."""
    branch = getattr(request, "branch", None)
    if branch is None:
        return {}
    today = timezone.localdate()
    out = {}
    if "student.view" in perms:
        from students.models import FollowUp
        from students.services import is_open_followup

        n = sum(1 for fu in FollowUp.objects.for_branch(branch).only("status", "next") if is_open_followup(fu) and fu.next and fu.next <= today)
        if n:
            out["students:followups"] = n
    if "project.approve" in perms:
        from akademik.models import FinalProject

        n = FinalProject.objects.filter(branch=branch, status=FinalProject.DIAJUKAN).count()
        if n:
            out["akademik:list"] = n
    if "session.view" in perms:
        from classes.models import Sesi

        n = Sesi.objects.for_branch(branch).filter(status="SCHEDULED", tgl__lt=today).count()
        if n:
            out["classes:sessions"] = n
    return out


def nav_for(request):
    caps = getattr(request, "caps", frozenset())
    if getattr(getattr(request, "user", None), "is_super_admin", False):
        caps = caps | {Cap.MANAGE_ALL}                # menu semua cabang juga tampil tanpa cabang aktif
    perms = perms_for_caps(caps)
    badges = nav_badges(request, perms)
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
            shown.append({"label": text, "href": href, "icon": icon, "active": active, "badge": badges.get(url_name, 0), "name": url_name})
        if shown:
            groups.append({"label": label, "items": shown})
    lit = [it for g in groups for it in g["items"] if it["active"]]
    best = max(lit, key=lambda it: len(it["href"]), default=None)     # /manajemen/ vs /manajemen/lifecycle/: yang paling spesifik
    for it in lit:
        it["active"] = it is best
    return groups


def nav_current(groups):
    """Menu aktif (judul kontekstual topbar bila halaman tidak memberi breadcrumb)."""
    return next((item for g in groups for item in g["items"] if item["active"]), None)


# Aksi cepat di topbar: (label, url name, izin, ikon) - hanya yang boleh dikerjakan pengguna
QUICK_ACTIONS = (
    ("Murid baru", "students:create", "student.create", "user-plus"),
    ("Orang tua baru", "students:parent_create", "parent.edit", "users-plus"),
    ("Follow-up baru", "students:followup_create", "followup.manage", "phone-plus"),
    ("Kelas baru", "classes:create", "class.manage", "school"),
    ("Guru baru", "masterdata:teacher_create", "teacher.manage", "user-star"),
)


def quick_actions(request):
    if getattr(request, "branch", None) is None:
        return []
    perms = perms_for_caps(getattr(request, "caps", frozenset()))
    out = []
    for text, url_name, need, icon in QUICK_ACTIONS:
        if need in perms:
            try:
                out.append({"label": text, "href": reverse(url_name), "icon": icon})
            except NoReverseMatch:
                continue
    return out
