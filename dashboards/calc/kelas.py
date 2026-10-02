"""Kelas = kolom rumus CLASS_MASTER dan C_KELAS (spesifikasi §3.5)."""
from collections import Counter
from dataclasses import dataclass

from .base import fold, same
from .status import kode_dipakai, semua_status_sekarang

HURUF_KAPASITAS = ("F", "P", "G", "S")
TIPE_KURSI = ("partner", "group")


@dataclass
class Kelas:
    row: object
    kapasitas: object
    aktif: int
    cuti: int
    status_kapasitas: str
    status_kelas: str
    kursi_kosong: float


def kapasitas(data, code):
    """INDEX(set_CapNilai, MATCH(LEFT(kode, 1), set_CapHuruf, 0)); "" bila huruf tidak dikenal."""
    huruf = (code or "")[:1].upper()
    return data.setting(huruf, "") if huruf in HURUF_KAPASITAS else ""


def daftar_kelas(data):
    def build():
        st = semua_status_sekarang(data)
        aktif, cuti = Counter(), Counter()
        for s in data.students:
            if not s.std:
                continue
            status = fold(st[fold(s.std)])
            if status == "active":
                aktif[fold(kode_dipakai(s))] += 1
            elif status == "on leave":
                cuti[fold(kode_dipakai(s))] += 1
        berisi = {fold(m.code) for m in data.members if m.std}
        out = []
        for c in data.classes:
            k = fold(c.code)
            n, nc, cap = aktif[k], cuti[k], kapasitas(data, c.code)
            angka = isinstance(cap, (int, float))
            if n == 0:
                st_cap = "KOSONG"
            elif angka and n > cap:
                st_cap = "OVER CAPACITY"
            elif angka and n == cap:
                st_cap = "FULL"
            else:
                st_cap = "NORMAL"
            st_kls = "ACTIVE" if n > 0 else "CUTI" if nc > 0 else "INACTIVE" if k in berisi else "UNKNOWN"
            kursi = max(cap - n, 0) if st_kls == "ACTIVE" and fold(c.tipe) in TIPE_KURSI and angka else 0
            out.append(Kelas(c, cap, n, nc, st_cap, st_kls, kursi))
        return out
    return data.memo("kelas", build)


def ringkasan_kelas(data):
    rows = daftar_kelas(data)
    return {"aktif": sum(k.status_kelas == "ACTIVE" for k in rows), "kursi": sum(k.kursi_kosong for k in rows),
            "penuh": sum(k.status_kapasitas == "FULL" for k in rows),
            "melebihi": sum(k.status_kapasitas == "OVER CAPACITY" for k in rows)}
