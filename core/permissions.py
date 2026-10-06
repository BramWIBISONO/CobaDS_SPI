"""Izin bernama (docs/PERMISSIONS.md) di atas kemampuan peran per cabang (core/capabilities.py).
Setiap aksi dicek di server lewat require_perm; tombol yang disembunyikan di template hanya kenyamanan."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .capabilities import ROLE_CAPS, Cap

PERMISSIONS = {
    "student.view": Cap.VIEW,                    # daftar & profil murid
    "student.create": Cap.STUDENT_WRITE,         # tambah murid
    "student.edit": Cap.STUDENT_WRITE,           # ubah data, kelas, guru, program, catatan
    "student.status": Cap.STATUS_CHANGE,         # cuti / OFF / aktif kembali / alumni
    "student.contacts": Cap.SEE_CONTACTS,        # nomor HP, WhatsApp, email, alamat
    "parent.view": Cap.VIEW,
    "parent.edit": Cap.STUDENT_WRITE,
    "class.view": Cap.VIEW,
    "class.manage": Cap.CLASS_WRITE,             # kelas baru, ubah, guru, anggota, jadwal
    "class.over_capacity": Cap.BRANCH_ADMIN,     # menambah murid aktif melebihi kapasitas
    "teacher.view": Cap.VIEW,
    "teacher.manage": Cap.CLASS_WRITE,
    "session.view": Cap.VIEW,
    "session.manage": Cap.SESSION_WRITE,         # semua sesi: realisasi, konfirmasi, batal, make-up
    "session.own": Cap.SESSION_WRITE_OWN,        # guru: sesi miliknya sendiri
    "attendance.manage": Cap.SESSION_WRITE,
    "attendance.own": Cap.SESSION_WRITE_OWN,
    "academic.manage": Cap.ACADEMIC_WRITE,
    "finance.view": Cap.VIEW,
    "payment.record": Cap.PAYMENT_EVIDENCE,      # catat pembayaran / bukti bayar
    "payment.verify": Cap.FINANCE_VERIFY,        # verifikasi, keputusan tagihan
    "billing.decide": Cap.FINANCE_VERIFY,
    "period.open": Cap.PERIOD_OPEN,              # BULAN BARU
    "period.close": Cap.PERIOD_CLOSE,            # TUTUP BULAN
    "off.manage": Cap.STATUS_CHANGE,
    "followup.manage": Cap.STUDENT_WRITE,
    "report.view": Cap.VIEW,
    "report.export": Cap.VIEW,
    "user.manage": Cap.BRANCH_ADMIN,
    "settings.manage": Cap.BRANCH_ADMIN,
    "import.run": Cap.BRANCH_ADMIN,
    "audit.view": Cap.AUDIT_VIEW,
    "branch.manage": Cap.MANAGE_ALL,
    "management.view": Cap.MANAGEMENT,           # Management Center, Business/Operational/Data Health, Lifecycle, laporan manajemen
    "management.finance": Cap.FINANCE_CONTROL,   # Finance Control, pratinjau & cetak Nota SPP
    "nota.issue": Cap.FINANCE_VERIFY,            # terbitkan nomor Nota SPP (NOTA_LOG)
    "project.submit": Cap.ACADEMIC_WRITE,        # ajukan final project murid (nilai rubrik, umpan balik)
    "project.approve": Cap.MANAGEMENT,           # setujui / tolak final project -> sertifikat & Student Report otomatis
}


def perms_for_caps(caps):
    return {name for name, cap in PERMISSIONS.items() if cap in caps}


def perms_for_role(role):
    return perms_for_caps(ROLE_CAPS.get(role, frozenset()))


def has_perm(request, name):
    return PERMISSIONS[name] in getattr(request, "caps", frozenset())


def has_any(request, *names):
    return any(has_perm(request, n) for n in names)


class PermSet:
    """Untuk template: {% if perm.student_edit %} == izin 'student.edit'."""

    def __init__(self, names):
        self._names = frozenset(names)

    def __getattr__(self, attr):
        if attr.startswith("_"):
            raise AttributeError(attr)
        return attr.replace("_", ".", 1) in self._names

    def __contains__(self, name):
        return name in self._names


def require_perm(*names):
    """Halaman/aksi cabang: login, cabang aktif, dan salah satu izin `names`."""
    for n in names:
        PERMISSIONS[n]                                      # nama salah = KeyError saat modul dimuat

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(request, *args, **kwargs):
            if getattr(request, "branch", None) is None:
                return redirect("core:home")
            if not has_any(request, *names):
                return render(request, "core/forbidden.html", status=403)
            return view(request, *args, **kwargs)
        return wrapped
    return decorator
