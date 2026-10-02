"""Status murid: Kelompok D_BULAN, Status Sekarang (STUDENT_MASTER), status akhir periode (C_MURID), nilai 'dipakai' (spesifikasi §3.2)."""
from .base import HIST_END, as_date, fold, month_end, yyyymm

PETA_BULAN = {"aktif": "ACTIVE", "baru": "ACTIVE", "rejoin": "ACTIVE", "cuti": "ON LEAVE", "off": "OFF"}


def kelompok(status):
    s = fold(status)
    if s in ("aktif", "baru", "rejoin"):
        return "Aktif"
    if s == "cuti":
        return "Cuti"
    if s == "off":
        return "Off"
    return ""


def event_terakhir(data, std, sampai):
    """Status event dengan Urutan terbesar (tanggal efektif lalu baris) pada/sebelum `sampai`; None bila tidak ada."""
    best = None
    for e in data.events_by_std.get(fold(std), ()):
        tgl = as_date(e.tgl)
        if tgl <= sampai and (best is None or (tgl, e.row_no) > (as_date(best.tgl), best.row_no)):
            best = e
    return None if best is None else (best.status or "")


def status_sekarang(data, student):
    ev = event_terakhir(data, student.std, data.today)
    if ev is not None:
        return ev
    return student.st_base if student.st_base else "PENDING"


def semua_status_sekarang(data):
    return data.memo("st_now", lambda: {fold(s.std): status_sekarang(data, s) for s in data.students if s.std})


def kode_dipakai(student):
    return student.kode_in if student.kode_in else (student.kode_read or "")


def guru_dipakai(student):
    return student.guru_in if student.guru_in else (student.guru or "")


def status_akhir_periode(data, student, mulai):
    ev = event_terakhir(data, student.std, month_end(mulai))
    if ev is not None:
        return ev
    if mulai <= HIST_END:
        row = data.bln_by_key.get(fold(f"{student.v1}|{yyyymm(mulai)}"))
        return PETA_BULAN.get(fold(row.status if row else ""), "")
    return student.st_base or ""
