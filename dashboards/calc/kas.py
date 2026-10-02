"""Buku kas & SPP = kolom rumus BUKU_KAS dan C_KAS (spesifikasi §3.4)."""
from collections import Counter
from dataclasses import dataclass

from .base import AGU_2026, BELUM_DIPUTUSKAN, JURNAL_TERSEMBUNYI, KAS_START, as_date, fold, num, round_half_up, same
from .laporan import baris_laporan

BUKAN_MURID = "BUKAN MURID"
STRIP = "—"
KEPUTUSAN = "perlu keputusan"
SUDAH, BELUM, SEBELUM_KAS = "Sudah ada pembayaran", "Belum ada pembayaran", "(belum ada buku kas)"


@dataclass
class KasRow:
    row: object
    dihitung: str
    s: list
    b: list

    def masuk_spp(self, bulan=None):
        """Baris yang dijumlah C_KAS: Jenis SPP, Dihitung YA (dan bulan itu bila diberikan)."""
        return same(self.row.jenis, "SPP") and same(self.dihitung, "YA") and (bulan is None or as_date(self.row.bulan) == bulan)


def label_murid(data):
    """lst_MuridAll: nama D_MURID, '[ID v1]' ditambahkan bila nama kembar; posisi ke-i = Student ID baris ke-i STUDENT_MASTER."""
    def build():
        names = Counter(fold(m.nama) for m in data.d_murid)
        out = {}
        for m, s in zip(data.d_murid, data.students):
            lab = f"{m.nama} [{m.v1}]" if names[fold(m.nama)] > 1 else (m.nama or "")
            out.setdefault(fold(lab), s.std or "")
        return out
    return data.memo("label_murid", build)


def _dua_jurnal(row):
    """Baris Agustus 2026 yang punya dua versi jurnal (rumus Dihitung & Student ID bergantung SETTINGS jurnal_agu)."""
    return as_date(row.bulan) == AGU_2026 and fold(row.versi)[:1] in ("t", "r")


def dihitung(data, row):
    """Nilai tersimpan; baris Agustus 2026 dua jurnal mengikuti SETTINGS jurnal_agu (versi 'T ·' tersembunyi, 'R ·' revisi)."""
    if _dua_jurnal(row):
        tersembunyi = same(data.setting("jurnal_agu", ""), JURNAL_TERSEMBUNYI)
        return "YA" if (fold(row.versi)[:1] == "t") == tersembunyi else "TIDAK"
    return row.dihitung or ""


def bagian(data, row):
    if _dua_jurnal(row) and same(data.setting("jurnal_agu", ""), BELUM_DIPUTUSKAN):
        return ["", "", "", ""], [0, 0, 0, 0]                    # Student ID 1-4 kosong selama jurnal belum diputuskan
    if row.kor1:
        labels = label_murid(data)
        s1 = "" if same(row.kor1, BUKAN_MURID) else labels.get(fold(row.kor1), "")
        s2 = "" if same(row.kor1, BUKAN_MURID) or not row.kor2 else labels.get(fold(row.kor2), "")
        s = [s1, s2, "", ""]
        nominal = num(row.nominal)
        b = [0 if not s1 else (nominal / 2 if s2 else nominal), 0 if not s2 else nominal / 2, 0, 0]
        return s, b
    s = [row.ss1 or "", row.ss2 or "", row.ss3 or "", row.ss4 or ""]
    b = [num(v) if sid else 0 for sid, v in zip(s, (row.sb1, row.sb2, row.sb3, row.sb4))]
    return s, b


def kas_rows(data):
    def build():
        out = []
        for r in data.kas:
            s, b = bagian(data, r)
            out.append(KasRow(r, dihitung(data, r), s, b))
        return out
    return data.memo("kas_rows", build)


def bulanan(data):
    out = []
    for bulan in data.kas_months:
        rows = [k for k in kas_rows(data) if k.masuk_spp(bulan)]
        total = sum(num(k.row.nominal) for k in rows)
        tertaut = sum(sum(k.b) for k in rows)
        out.append([bulan, total, tertaut, total - tertaut])
    return out


def perlu_keputusan(data, bulan):
    return bulan == AGU_2026 and same(data.setting("jurnal_agu", ""), BELUM_DIPUTUSKAN)


def spp_murid(data, bulan):
    def build():
        if bulan < KAS_START:
            return {}
        out = Counter()
        for k in kas_rows(data):
            if k.masuk_spp(bulan):
                for sid, amount in zip(k.s, k.b):
                    if sid:
                        out[fold(sid)] += amount
        return dict(out)
    return data.memo(("spp_murid", bulan), build)


def status_bayar(data, bulan, spp, kelompok):
    if bulan < KAS_START:
        return SEBELUM_KAS
    if perlu_keputusan(data, bulan):
        return KEPUTUSAN
    if spp > 0:
        return SUDAH
    return BELUM if kelompok == "Aktif" else ""


def _total(data, bulan):
    return sum(num(k.row.nominal) for k in kas_rows(data) if k.masuk_spp(bulan))


def ringkasan_spp(data, f):
    bulan, keputusan = f.bulan, perlu_keputusan(data, f.bulan)
    per_std = spp_murid(data, bulan)
    per_baris, belum = {}, []
    aktif = sudah = 0
    for b in baris_laporan(data, f):
        spp = 0 if bulan < KAS_START else per_std.get(fold(b.std), 0)
        st = status_bayar(data, bulan, spp, b.kelompok)
        per_baris[id(b.murid)] = (spp, st)
        if b.ikut and b.kelompok == "Aktif":
            aktif += 1
            sudah += spp > 0
        if b.ikut and st == BELUM:
            belum.append(b)
    sebelum = bulan < KAS_START
    rows = [k for k in kas_rows(data) if k.masuk_spp(bulan)]
    tertaut_kosong = sum(1 for k in rows if not k.s[0]) - sum(1 for k in rows if same(k.row.kor1, BUKAN_MURID))
    ytd = sum(t for m, t, _l, _n in bulanan(data) if m.year == bulan.year and m <= bulan)
    lemah = sum(1 for k in kas_rows(data) if fold(k.row.yakin).startswith("lemah") and not k.row.kor1)
    if sebelum:
        sudah_txt = belum_n = STRIP
    elif keputusan:
        sudah_txt = belum_n = KEPUTUSAN
    else:
        sudah_txt = 0 if aktif == 0 else f"{sudah}  ·  {round_half_up(sudah / aktif * 100)}%"
        belum_n = len(belum)
    return {
        "spp": [STRIP if sebelum else _total(data, bulan), STRIP if sebelum else ytd, aktif, sudah_txt, belum_n,
                STRIP if sebelum or keputusan else tertaut_kosong, lemah],
        "per_baris": per_baris,
        "belum_bayar": [] if keputusan or sebelum else belum,
        "keputusan": keputusan,
    }


def kas_terakhir(data):
    months = data.kas_months
    if not months:
        return None
    last = months[-1]
    prev = months[-2] if len(months) > 1 else None
    tgls = [as_date(r.tgl) for r in data.kas if as_date(r.bulan) == last and as_date(r.tgl)]
    return {"bulan": last, "total": _total(data, last), "tgl": max(tgls) if tgls else None,
            "prev_bulan": prev, "prev_total": _total(data, prev) if prev else 0}
