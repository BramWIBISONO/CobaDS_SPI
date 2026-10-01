"""Hak akses (spesifikasi §9): peran per cabang -> kemampuan. Dicek di server untuk setiap aksi."""
from enum import StrEnum


class Cap(StrEnum):
    MANAGE_ALL = "manage_all"              # semua cabang, buat cabang, pengguna semua cabang, konfigurasi SPI
    BRANCH_ADMIN = "branch_admin"          # pengguna & SETTINGS cabang, impor migrasi
    VIEW = "view"                          # semua halaman & laporan cabang, ekspor
    STUDENT_WRITE = "student_write"        # Murid Baru / Update Murid / Lead / Follow-up
    DOCUMENT_WRITE = "document_write"      # Dokumen
    STATUS_CHANGE = "status_change"        # Perubahan Status (cuti / OFF / aktif kembali)
    PAYMENT_EVIDENCE = "payment_evidence"  # bukti bayar (PB)
    FINANCE_VERIFY = "finance_verify"      # verifikasi, keputusan tagihan, koreksi periode kas, unggah kas, nota
    PERIOD_OPEN = "period_open"            # BULAN BARU
    PERIOD_CLOSE = "period_close"          # TUTUP BULAN
    CLASS_WRITE = "class_write"            # Guru & Kelas Baru, Jadwal, Simulasi
    ACADEMIC_WRITE = "academic_write"      # Akademik
    SESSION_WRITE = "session_write"        # realisasi pertemuan / kegiatan guru (semua sesi)
    SESSION_WRITE_OWN = "session_write_own"  # realisasi sesi milik guru itu sendiri
    SEE_CONTACTS = "see_contacts"          # kontak orang tua / murid
    DATA_VALIDATE = "data_validate"        # Data Quality, CEK NAMA, issue


ALL_CAPS = frozenset(Cap)
ROLE_CAPS = {
    "BRANCH_ADMIN": ALL_CAPS - {Cap.MANAGE_ALL},
    "MANAGER": frozenset({Cap.VIEW, Cap.STUDENT_WRITE, Cap.DOCUMENT_WRITE, Cap.STATUS_CHANGE, Cap.PERIOD_OPEN, Cap.PERIOD_CLOSE,
                          Cap.CLASS_WRITE, Cap.ACADEMIC_WRITE, Cap.SESSION_WRITE, Cap.SEE_CONTACTS, Cap.DATA_VALIDATE}),
    "CSO": frozenset({Cap.VIEW, Cap.STUDENT_WRITE, Cap.DOCUMENT_WRITE, Cap.STATUS_CHANGE, Cap.PAYMENT_EVIDENCE, Cap.CLASS_WRITE,
                      Cap.SESSION_WRITE, Cap.SEE_CONTACTS, Cap.DATA_VALIDATE}),
    "FINANCE": frozenset({Cap.VIEW, Cap.PAYMENT_EVIDENCE, Cap.FINANCE_VERIFY, Cap.PERIOD_OPEN, Cap.SEE_CONTACTS, Cap.DATA_VALIDATE}),
    "ACADEMIC": frozenset({Cap.VIEW, Cap.DOCUMENT_WRITE, Cap.CLASS_WRITE, Cap.ACADEMIC_WRITE, Cap.SESSION_WRITE, Cap.DATA_VALIDATE}),
    "TEACHER": frozenset({Cap.SESSION_WRITE_OWN}),
}
ROLE_LABELS = {"SUPER_ADMIN": "Super Admin", "BRANCH_ADMIN": "Branch Admin", "MANAGER": "Manager", "CSO": "CSO",
               "FINANCE": "Finance", "ACADEMIC": "Academic", "TEACHER": "Teacher"}


def role_of(user, branch):
    if branch is None or not getattr(user, "is_authenticated", False):
        return None
    if user.is_super_admin:
        return "SUPER_ADMIN"
    membership = user.memberships.filter(branch=branch).only("role").first()
    return membership.role if membership else None


def caps_for(user, branch):
    role = role_of(user, branch)
    if role == "SUPER_ADMIN":
        return ALL_CAPS
    return ROLE_CAPS.get(role, frozenset())
