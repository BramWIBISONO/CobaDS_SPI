"""Laporan bulanan murid = C_DASH / C_LIST (spesifikasi §3.3). Baris = D_MURID (urutan sheet); data bulan = D_BULAN kunci 'ID v1|yyyymm'."""
from collections import Counter
from dataclasses import dataclass

from .base import HIST_MONTHS, SEMUA, add_months, as_date, fold, program_of, same, short_label, yyyymm
from .status import kelompok

STATUS_GRAFIK = ["Aktif", "Baru", "Rejoin", "Cuti", "Off"]
LAINNYA = "Lainnya / kosong"


@dataclass(frozen=True)
class Filter:
    bulan: object                       # date hari pertama bulan (salah satu HIST_MONTHS)
    program: str = SEMUA
    tipe: str = SEMUA
    mode: str = SEMUA
    guru: str = SEMUA

    def lolos(self, row):
        """Rumus K C_DASH / SUMPRODUCT tren: 'Semua' lolos; selain itu sama (tanpa beda huruf) dengan nilai baris bulan."""
        return all(same(want, SEMUA) or same(have, want) for want, have in (
            (self.program, program_of(row.grade)), (self.tipe, row.tipe), (self.mode, row.mode), (self.guru, row.guru)))


@dataclass
class Baris:
    murid: object
    row: object
    status: str
    kelompok: str
    ikut: bool
    off_baru: bool

    def _bulan(self, name):
        return (getattr(self.row, name) or "") if self.row else ""

    v1 = property(lambda self: self.murid.v1 or "")
    nama = property(lambda self: self.murid.nama or "")
    std = property(lambda self: self.murid.std or "")
    kode_kelas = property(lambda self: self.murid.kode_kelas or "")
    level = property(lambda self: self._bulan("grade"))
    program = property(lambda self: program_of(self._bulan("grade")))
    guru = property(lambda self: self._bulan("guru"))
    tipe = property(lambda self: self._bulan("tipe"))
    mode = property(lambda self: self._bulan("mode"))


def _row(data, v1, bulan):
    return data.bln_by_key.get(fold(f"{v1}|{yyyymm(bulan)}"))


def baris_laporan(data, f):
    def build():
        prev = add_months(f.bulan, -1) if f.bulan != HIST_MONTHS[0] else None
        out = []
        for m in data.d_murid:
            row = _row(data, m.v1, f.bulan)
            status = (row.status or "") if row else ""
            kel = kelompok(status) if row else ""
            ikut = row is not None and f.lolos(row)
            st_prev = ""
            if prev is not None:
                prow = _row(data, m.v1, prev)
                st_prev = (prow.status or "") if prow else ""
            off_baru = ikut and same(status, "Off") and st_prev != "" and not same(st_prev, "Off")
            out.append(Baris(m, row, status, kel, ikut, off_baru))
        return out
    return data.memo(("baris", f), build)


def _count(rows, key, wanted):
    return sum(1 for b in rows if same(key(b), wanted))


def ringkasan_murid(data, f):
    rows = [b for b in baris_laporan(data, f) if b.ikut]
    aktif = [b for b in rows if b.kelompok == "Aktif"]
    n_kel = Counter(b.kelompok for b in rows)
    murid = [n_kel["Aktif"] + n_kel["Cuti"], n_kel["Aktif"], _count(rows, lambda b: b.status, "Baru"),
             _count(rows, lambda b: b.status, "Rejoin"), n_kel["Cuti"], n_kel["Off"], sum(b.off_baru for b in rows)]
    gurus = data.gurus[:10]
    guru = [[g, _count(aktif, lambda b: b.guru, g)] for g in gurus]
    guru.append([LAINNYA, len(aktif) - sum(n for _g, n in guru)])
    return {
        "murid": murid,
        "status": [[s, _count(rows, lambda b: b.status, s)] for s in STATUS_GRAFIK],
        "level": [[lv, _count(aktif, lambda b: b.level, lv)] for lv in data.levels],
        "tipe": [[t, _count(aktif, lambda b: b.tipe, t)] for t in data.tipes],
        "guru": guru,
        "tren": tren(data, f),
        "baru": [b for b in rows if same(b.status, "Baru")],
        "off_baru": [b for b in rows if b.off_baru],
        "daftar": rows,
    }


def tren(data, f):
    """33 bulan, semua baris D_BULAN (juga yang tanpa D_MURID), filter selain bulan."""
    def build():
        per = {m: Counter() for m in HIST_MONTHS}
        for r in data.d_bulan:
            b = as_date(r.bulan)
            if b in per and f.lolos(r):
                per[b][kelompok(r.status)] += 1
                per[b]["baru"] += same(r.status, "Baru")
        return [[short_label(m), c["Aktif"], c["Cuti"], c["Off"], c["baru"]] for m, c in per.items()]
    return data.memo(("tren", f.program, f.tipe, f.mode, f.guru), build)
