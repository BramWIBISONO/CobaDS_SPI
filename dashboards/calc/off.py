"""Murid OFF = kolom rumus STUDENT_OFF dan ringkasan C_OFF (spesifikasi §3.6). Hanya baris ber-Off Record ID."""
from dataclasses import dataclass

from .base import add_months, as_date, fold, months_between, num, same

MASIH_OFF = "MASIH OFF"
KEMBALI = "KEMBALI (aktif lagi · INPUT CENTER)"
PERLU = ("MENDESAK", "HARI INI", "MINGGU INI")


@dataclass
class Off:
    row: object
    status: str
    lama: object
    aksi: str
    fu_tgl: object
    fu_next: object
    prioritas: str


def _status(data, r):
    src = r.status_src or ""
    mulai = as_date(r.tgl) or as_date(r.month)
    if (src == "" or same(src, MASIH_OFF)) and mulai and any(
            same(e.status, "ACTIVE") and as_date(e.tgl) >= mulai for e in data.events_by_std.get(fold(r.std), ())):
        return KEMBALI
    return src or MASIH_OFF


def _prioritas(data, status, lama, aksi, fu_tgl, fu_next, month):
    if not same(status, MASIH_OFF):
        return "SELESAI" if fold(status).startswith("kembali") else "PANTAU"
    if same(aksi, "Kasus ditutup"):
        return "SELESAI"
    if fu_next and fu_next <= data.today:
        return "HARI INI"
    if not aksi and not fu_tgl and month and month >= add_months(data.bulan_ini, -1):
        return "MENDESAK"
    if not aksi and not fu_tgl and num(lama) <= num(data.setting("off_lama", 0)):
        return "MINGGU INI"
    return "PANTAU"


def daftar_off(data):
    def build():
        out = []
        for r in data.offs:
            if not r.off_id:
                continue
            month = as_date(r.month)
            status = _status(data, r)
            lama = ""
            if same(status, MASIH_OFF):
                lama = (months_between(month, data.bulan_ini) or 0) if month else 0
            fus = [f for f in data.followups_by_std.get(fold(r.std), ()) if month and as_date(f.tgl) and as_date(f.tgl) >= month]
            aksi = next((f.aksi for f in reversed(fus) if f.aksi), "")
            fu_tgl = max((as_date(f.tgl) for f in fus), default=None)
            fu_next = next((as_date(f.next) for f in reversed(fus) if f.next), None)
            out.append(Off(r, status, lama, aksi, fu_tgl, fu_next, _prioritas(data, status, lama, aksi, fu_tgl, fu_next, month)))
        return out
    return data.memo("off", build)


def ringkasan_off(data):
    rows = daftar_off(data)
    return {"masih": sum(same(o.status, MASIH_OFF) for o in rows), "perlu": sum(o.prioritas in PERLU for o in rows),
            "baru": sum(as_date(o.row.month) == data.bulan_ini for o in rows)}
