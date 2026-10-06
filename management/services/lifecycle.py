"""Student Lifecycle = sheet MATRIKS Excel, plus bulan sesudah riwayat DB Murid dari STATUS_EVENT.

Satu baris = satu murid (STUDENT_MASTER), satu sel = satu bulan:
  A Aktif · B Baru · R Rejoin · C Cuti · O Off            (D_BULAN kunci 'ID v1|yyyymm', rumus MATRIKS)
  ? status kosong / tidak tercatat · – belum masuk SPI · · tidak tercatat setelah Off
Bulan sesudah HIST_END (Sep 2026): status akhir bulan dari STATUS_EVENT, bila belum ada event = Status Awal (calc.status).
  ACTIVE -> B bila sel sebelumnya '–' (baru masuk), R bila sebelumnya O/· (kembali dari Off), selain itu A
  ON LEAVE -> C · OFF -> '·' bila sebelumnya '·', selain itu O · PENDING -> ? · kosong -> aturan 'tidak ada catatan'
"""
from collections import Counter
from dataclasses import dataclass, field

from dashboards.calc.base import HIST_END, HIST_MONTHS, add_months, fold, label, period_code, short_label, yyyymm
from dashboards.calc.status import event_terakhir, guru_dipakai, kode_dipakai, status_akhir_periode

BELUM_MASUK, SETELAH_OFF, KOSONG = "–", "·", "?"
HURUF = {"aktif": "A", "baru": "B", "rejoin": "R", "cuti": "C", "off": "O", "": KOSONG}
ARTI = {"A": "Aktif", "B": "Baru", "R": "Rejoin", "C": "Cuti", "O": "Off", KOSONG: "Status kosong / tidak tercatat",
        BELUM_MASUK: "Belum masuk SPI", SETELAH_OFF: "Tidak tercatat setelah Off"}
AKTIF = frozenset("ABR")
TERDAFTAR = frozenset("ABRC")                 # basis murid berjalan = Aktif + Cuti (sama dengan 'Total data murid' Laporan)
OFF_POOL = frozenset(("O", SETELAH_OFF))

# Definisi eksplisit (DB Murid tidak punya rumus retensi; Laporan Excel menulis 'TIDAK TERSEDIA'). Ditampilkan di UI.
DEFINISI = [
    ("Murid aktif", "A + B + R pada bulan itu (Aktif + Baru + Rejoin, sama dengan Laporan Murid)."),
    ("Basis murid", "A + B + R + C pada bulan sebelumnya (murid aktif dan cuti)."),
    ("Retensi", "Murid basis bulan sebelumnya yang bulan ini masih A/B/R/C ÷ basis bulan sebelumnya."),
    ("Churn (Off baru)", "Murid basis bulan sebelumnya yang bulan ini O ÷ basis bulan sebelumnya (Off baru = Laporan Murid)."),
    ("Hilang dari catatan", "Murid basis bulan sebelumnya yang bulan ini ?, – atau · (bukan Off) - masalah data, bukan churn."),
    ("Reaktivasi", "R bulan ini ÷ murid yang bulan sebelumnya O atau · (pool Off)."),
    ("Konversi baru → aktif", "Murid B bulan sebelumnya yang bulan ini A/B/R/C ÷ murid B bulan sebelumnya."),
]


def months_until(today):
    """Jan 2024 ... bulan berjalan (riwayat DB Murid lalu bulan sesudahnya)."""
    out = list(HIST_MONTHS)
    now = today.replace(day=1)
    while out[-1] < now:
        out.append(add_months(out[-1], 1))
    return out


def _tanpa_catatan(prev):
    if prev in (None, BELUM_MASUK):
        return BELUM_MASUK
    if prev in OFF_POOL:
        return SETELAH_OFF
    return KOSONG


def _sesudah_riwayat(status, prev):
    s = fold(status)
    if s == "active":
        return "B" if prev in (None, BELUM_MASUK) else "R" if prev in OFF_POOL else "A"
    if s == "on leave":
        return "C"
    if s == "off":
        return SETELAH_OFF if prev == SETELAH_OFF else "O"
    if s == "pending":
        return KOSONG
    return _tanpa_catatan(prev)


@dataclass
class Baris:
    murid: object
    huruf: list
    raw: list = field(default_factory=list)

    std = property(lambda self: self.murid.std or "")
    nama = property(lambda self: self.murid.nama or "")
    v1 = property(lambda self: self.murid.v1 or "")
    kode = property(lambda self: kode_dipakai(self.murid))
    guru = property(lambda self: guru_dipakai(self.murid))
    program = property(lambda self: self.murid.prog_in or self.murid.program or "")
    level = property(lambda self: self.murid.level_in or self.murid.level or "")
    mode = property(lambda self: self.murid.mode or "")
    tipe = property(lambda self: self.murid.tipe_kode or self.murid.tipe_asli or "")

    @property
    def bulan_aktif(self):
        # MATRIKS Excel counts only its fixed Jan 2024-Sep 2026 columns.
        return sum(h in AKTIF for h in self.huruf[:len(HIST_MONTHS)])

    @property
    def bulan_aktif_sampai_sekarang(self):
        return sum(h in AKTIF for h in self.huruf)

    @property
    def terakhir(self):
        return self.raw[-1] if self.raw else ""

    @property
    def status_terakhir_historis(self):
        index = len(HIST_MONTHS) - 1
        return self.raw[index] if len(self.raw) > index else ""

    @property
    def kode_terakhir(self):
        return self.huruf[-1] if self.huruf else BELUM_MASUK


def matrix(data):
    """Semua murid ber-Student ID (urutan STUDENT_MASTER) × months_until(today)."""
    def build():
        months = months_until(data.today)
        out = []
        for s in data.students:
            if not s.std:
                continue
            huruf, raw, prev = [], [], None
            for m in months:
                if m <= HIST_END:
                    row = data.bln_by_key.get(fold(f"{s.v1}|{yyyymm(m)}")) if s.v1 else None
                    if row is None:
                        h, r = _tanpa_catatan(prev), ""
                    else:
                        r = row.status or ""
                        h = HURUF.get(fold(r), BELUM_MASUK)
                else:
                    if m == data.bulan_ini:
                        r = event_terakhir(data, s.std, data.today)
                        if r is None:
                            r = s.st_base or ""
                    else:
                        r = status_akhir_periode(data, s, m)
                    h = _sesudah_riwayat(r, prev)
                huruf.append(h)
                raw.append(r)
                prev = h
            out.append(Baris(s, huruf, raw))
        return out
    return data.memo("mgmt_matrix", build)


def months(data):
    return months_until(data.today)


def kpi_bulan(rows, i):
    """Angka lifecycle bulan ke-i (definisi di DEFINISI)."""
    cur = Counter(b.huruf[i] for b in rows)
    out = {"aktif": sum(cur[h] for h in AKTIF), "baru": cur["B"], "rejoin": cur["R"], "cuti": cur["C"], "off": cur["O"],
           "kosong": cur[KOSONG], "basis": None, "retensi": None, "churn": None, "off_baru": None, "hilang": None,
           "reaktivasi": None, "konversi": None, "terdaftar": sum(cur[h] for h in TERDAFTAR)}
    if i == 0:
        return out
    basis = [b for b in rows if b.huruf[i - 1] in TERDAFTAR]
    pool = [b for b in rows if b.huruf[i - 1] in OFF_POOL]
    baru = [b for b in rows if b.huruf[i - 1] == "B"]
    tetap = sum(b.huruf[i] in TERDAFTAR for b in basis)
    off_baru = sum(b.huruf[i] == "O" for b in basis)
    out.update({
        "basis": len(basis), "tetap": tetap, "off_baru": off_baru, "hilang": len(basis) - tetap - off_baru,
        "retensi": _pct(tetap, len(basis)), "churn": _pct(off_baru, len(basis)),
        "reaktivasi": _pct(cur["R"], len(pool)), "pool_off": len(pool),
        "konversi": _pct(sum(b.huruf[i] in TERDAFTAR for b in baru), len(baru)), "baru_lalu": len(baru),
    })
    return out


def _pct(a, b):
    return round(a * 100 / b, 1) if b else None


def series(data, rows=None):
    """KPI semua bulan untuk grafik & perbandingan (bulan lalu, tahun lalu, 3/6/12 bulan)."""
    rows = matrix(data) if rows is None else rows
    ms = months(data)
    return [{"bulan": m, "label": label(m), "short": short_label(m), "kode": period_code(m), **kpi_bulan(rows, i)} for i, m in enumerate(ms)]


def streak(huruf, letters):
    """Panjang deret huruf di ujung (bulan terakhir mundur) yang termasuk `letters`."""
    n = 0
    for h in reversed(huruf):
        if h not in letters:
            break
        n += 1
    return n


def wawasan(data, rows=None):
    """Kelompok murid untuk perhatian manajemen - semua dari huruf matriks (bisa ditelusuri ke sel)."""
    rows = matrix(data) if rows is None else rows
    cuti_lama = int(float(data.setting("cuti_lama", 2) or 2))
    out = {"mendekati_off": [], "baru_off": [], "kembali": [], "lama_tidak_aktif": [], "status_kosong": [], "tidak_biasa": []}
    for b in rows:
        h = b.huruf
        if not h:
            continue
        if h[-1] == "C" and streak(h, {"C"}) >= cuti_lama:
            out["mendekati_off"].append((b, f"cuti {streak(h, {'C'})} bulan berturut-turut (batas cuti lama: {cuti_lama})"))
        for k in (1, 2):
            if len(h) > k and h[-k] == "O" and h[-k - 1] in TERDAFTAR:
                out["baru_off"].append((b, f"Off sejak {short_label(months(data)[-k])}"))
                break
        recent = h[-3:]
        if "R" in recent:
            out["kembali"].append((b, "rejoin dalam 3 bulan terakhir"))
        n_off = streak(h, OFF_POOL)
        if n_off >= 6 and any(x in TERDAFTAR for x in h):
            out["lama_tidak_aktif"].append((b, f"tidak aktif {n_off} bulan"))
        if KOSONG in recent and any(x in TERDAFTAR for x in h[-6:]):
            out["status_kosong"].append((b, "status kosong di 3 bulan terakhir"))
        last12 = [x for x in h[-12:] if x not in (BELUM_MASUK, SETELAH_OFF)]
        changes = sum(1 for a, c in zip(last12, last12[1:]) if (a in AKTIF) != (c in AKTIF) or (a == "C") != (c == "C"))
        if changes >= 4:
            out["tidak_biasa"].append((b, f"{changes} kali berganti status dalam 12 bulan"))
    return out


def filtered(rows, *, q="", program="", kode="", guru="", mode="", status="", kolom=-1):
    """Saringan matriks: teks, program, kode kelas, guru, mode, dan huruf status pada kolom bulan `kolom` (bawaan bulan terakhir)."""
    qf = fold(q).strip()
    out = []
    for b in rows:
        if qf and qf not in fold(b.nama) and qf not in fold(b.std) and qf not in fold(b.v1):
            continue
        if program and fold(program) not in (fold(b.program), fold(b.level).split(" ")[0]):
            continue
        if kode and fold(kode) != fold(b.kode):
            continue
        if guru and fold(guru) != fold(b.guru):
            continue
        if mode and fold(mode) != fold(b.mode):
            continue
        if status:
            want = set(status) if status != "aktif" else AKTIF
            if b.huruf[kolom] not in want:
                continue
        out.append(b)
    return out
