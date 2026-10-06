"""Finance Control & Nota SPP - satu sumber untuk status bayar per murid per periode tagihan.

Rumus = sheet NOTA (v3_pages.py Z1-Z14) dan SPP_TAGIHAN (v4_build_sheets.py):
  Periode tagihan baris BUKU_KAS  = 'Periode Tagihan (koreksi)' bila diisi, selain itu '(sistem)'          (bk_Per)
  Diterima (buku kas)             = bagian murid di baris SPP, Dihitung = YA, periode tagihan = periode     (calc.kas.bagian)
  Periode < mulai_v4 (Okt 2026)   : tagihan = Harga SPP dipakai (harga ubah, lalu harga); LUNAS / SEBAGIAN / BELUM TERCATAT
  Periode >= mulai_v4             : tagihan = baris SPP_TAGIHAN (harga - diskon + penyesuaian); tanpa baris = TIDAK ADA TAGIHAN
  Agustus 2026 & jurnal belum diputuskan = PERLU KEPUTUSAN (nota tidak bisa dibuat)
Tidak ada angka yang diketik: semua dari BUKU_KAS, STUDENT_MASTER, SPP_TAGIHAN, BUKTI_BAYAR.
"""
import datetime
from collections import defaultdict
from dataclasses import dataclass, field

from dashboards.calc.base import AGU_2026, BELUM_DIPUTUSKAN, KAS_START, as_date, fold, label, month_end, num, parse_period, period_code, same
from dashboards.calc.kas import BUKAN_MURID, kas_rows
from dashboards.calc.status import event_terakhir, guru_dipakai, kode_dipakai
from finance.models import BuktiBayar, NotaLog, Pembayar, SppTagihan
from students.models import ParentMaster

from .lifecycle import AKTIF, matrix, months

LUNAS, SEBAGIAN, BELUM = "LUNAS", "SEBAGIAN", "BELUM TERCATAT"
KEPUTUSAN, TANPA_HARGA, TANPA_TAGIHAN = "PERLU KEPUTUSAN", "HARGA BELUM TERCATAT", "TIDAK ADA TAGIHAN"
MENUNGGU = "MENUNGGU VERIFIKASI"
DAPAT_NOTA = {LUNAS, SEBAGIAN, BELUM, MENUNGGU, "BELUM DIBAYAR", "TERLAMBAT", "BELUM JATUH TEMPO", "PERLU KLARIFIKASI",
              "PEMBAYARAN PERIODE BERBEDA"}
NADA = {LUNAS: "st-baik", SEBAGIAN: "st-info", MENUNGGU: "st-info", BELUM: "st-perhatian", "BELUM DIBAYAR": "st-perhatian",
        "BELUM JATUH TEMPO": "st-netral", "TERLAMBAT": "st-kritis", KEPUTUSAN: "st-serius", TANPA_HARGA: "st-kritis",
        TANPA_TAGIHAN: "st-netral", "DIBEBASKAN": "st-netral", "PERLU KLARIFIKASI": "st-serius", "PEMBAYARAN PERIODE BERBEDA": "st-serius"}


def per_dipakai(row):
    return str(row.per_in or row.per_sys or "").strip()


def harga_dipakai(student):
    for v in (student.harga_in, student.harga):
        if v is not None:
            return float(v)
    return None


def mulai_v4(data):
    v = data.setting("mulai_v4")
    d = as_date(v) or parse_period(str(v)[:7]) if v else None
    return d or datetime.date(2026, 10, 1)


def keputusan_agustus(data, bulan):
    return bulan == AGU_2026 and same(data.setting("jurnal_agu", ""), BELUM_DIPUTUSKAN)


def kas_per_periode(data):
    """{(periode 'yyyy-mm', std fold): {'total': rp, 'baris': [(baris kas, bagian)]}} + {(bulan kas, std): total}."""
    def build():
        per, per_bulan = defaultdict(lambda: {"total": 0.0, "baris": []}), defaultdict(float)
        for k in kas_rows(data):
            if not same(k.row.jenis, "SPP") or not same(k.dihitung, "YA"):
                continue
            p = per_dipakai(k.row)
            for sid, amount in zip(k.s, k.b):
                if sid and amount:
                    key = fold(sid)
                    if p:
                        per[(p, key)]["total"] += amount
                        per[(p, key)]["baris"].append((k.row, amount))
                    if as_date(k.row.bulan):
                        per_bulan[(period_code(as_date(k.row.bulan)), key)] += amount
        return dict(per), dict(per_bulan)
    return data.memo("mgmt_kas_per", build)


def tagihan_resmi(data):
    def build():
        out = {}
        for t in SppTagihan.objects.for_branch(data.branch).order_by("row_no"):
            out.setdefault((str(t.per).strip(), fold(t.std)), t)
        return out
    return data.memo("mgmt_tagihan", build)


def bukti_per(data):
    def build():
        out = defaultdict(lambda: {"verified": 0.0, "wait": 0.0, "cek": 0})
        for b in BuktiBayar.objects.for_branch(data.branch):
            key = (str(b.per).strip(), fold(b.std))
            if same(b.ver, "Verified"):
                out[key]["verified"] += num(float(b.nominal or 0))
            elif same(b.ver, "Belum Diverifikasi"):
                out[key]["wait"] += num(float(b.nominal or 0))
            elif same(b.ver, "Perlu Klarifikasi") or same(b.ver, "Tidak Cocok"):
                out[key]["cek"] += 1
        return dict(out)
    return data.memo("mgmt_bukti", build)


@dataclass
class StatusBayar:
    murid: object
    bulan: datetime.date
    tagihan: object                     # float / None
    bayar: float
    status: str
    sumber: str                         # 'harga SPP' / 'SPP_TAGIHAN'
    baris: list = field(default_factory=list)
    menunggu: float = 0.0
    pesan: str = ""

    @property
    def sisa(self):
        return None if self.tagihan is None else max(0.0, self.tagihan - self.bayar)

    @property
    def nada(self):
        return NADA.get(self.status, "st-netral")

    @property
    def bisa_nota(self):
        return self.status in DAPAT_NOTA and self.tagihan is not None


def status_bayar(data, student, bulan):
    per = period_code(bulan)
    key = (per, fold(student.std))
    kas, per_bulan = kas_per_periode(data)
    paid_kas = kas.get(key, {}).get("total", 0.0)
    baris = kas.get(key, {}).get("baris", [])
    if keputusan_agustus(data, bulan):
        return StatusBayar(student, bulan, harga_dipakai(student), 0.0, KEPUTUSAN, "harga SPP", baris,
                           pesan="Agustus 2026: jurnal penerimaan perlu keputusan (SETTINGS) - nota belum bisa dibuat.")
    if bulan >= mulai_v4(data):
        t = tagihan_resmi(data).get(key)
        if t is None:
            return StatusBayar(student, bulan, None, paid_kas, TANPA_TAGIHAN, "SPP_TAGIHAN", baris,
                               pesan="Tidak ada tagihan SPP murid ini untuk periode ini (belum BULAN BARU, atau murid ON LEAVE / OFF / PENDING).")
        return _status_tagihan(data, student, bulan, t, paid_kas, per_bulan, baris)
    harga = harga_dipakai(student)
    if harga is None:
        return StatusBayar(student, bulan, None, paid_kas, TANPA_HARGA, "harga SPP", baris,
                           pesan="Harga SPP murid ini belum tercatat (angka) - isi lewat Ubah Murid.")
    st = LUNAS if paid_kas >= harga else SEBAGIAN if paid_kas > 0 else BELUM
    return StatusBayar(student, bulan, harga, paid_kas, st, "harga SPP", baris)


def _status_tagihan(data, student, bulan, t, paid_kas, per_bulan, baris):
    """Kolom status SPP_TAGIHAN (v4_build_sheets.py) dengan label nota (Z8)."""
    due = num(float(t.harga or 0)) - num(float(t.diskon or 0)) + num(float(t.adj or 0))
    b = bukti_per(data).get((period_code(bulan), fold(student.std)), {"verified": 0.0, "wait": 0.0, "cek": 0})
    paid = max(paid_kas, b["verified"])
    std = student.std
    st_awal = event_terakhir(data, std, bulan) or (student.st_base or "")
    st_akhir = event_terakhir(data, std, month_end(bulan)) or (student.st_base or "")
    lain = per_bulan.get((period_code(bulan), fold(std)), 0.0) - paid_kas > 0
    if t.keputusan:
        status = t.keputusan
    elif due <= 0:
        status = "Dibebaskan"
    elif paid >= due - 0.5:
        status = "Sudah Dibayar"
    elif b["wait"] > 0:
        status = "Menunggu Verifikasi"
    elif paid > 0 or b["cek"] > 0 or (fold(st_awal) != "active" and fold(st_akhir) != "active"):
        status = "Perlu Klarifikasi"
    elif lain:
        status = "Pembayaran Periode Berbeda"
    elif data.today < datetime.date(bulan.year, bulan.month, min(28, int(num(float(data.setting("jatuh_tempo", 1) or 1))) or 1)):
        status = "Belum Jatuh Tempo"
    elif data.today > month_end(bulan):
        status = "Terlambat"
    else:
        status = "Belum Dibayar"
    nota = LUNAS if status == "Sudah Dibayar" else MENUNGGU if status == "Menunggu Verifikasi" else SEBAGIAN if paid > 0 else status.upper()
    return StatusBayar(student, bulan, due, paid, nota, "SPP_TAGIHAN", baris, menunggu=b["wait"])


def catatan_kas(data, bulan):
    """Mengapa angka pembayaran periode ini mungkin belum lengkap (ditampilkan di samping angka, bukan disembunyikan)."""
    out = []
    jarak = abs((bulan.year * 12 + bulan.month) - (AGU_2026.year * 12 + AGU_2026.month))
    if same(data.setting("jurnal_agu", ""), BELUM_DIPUTUSKAN) and jarak <= 1:
        out.append("Uang yang masuk di buku kas Agustus 2026 belum dihitung (jurnal belum diputuskan), jadi pembayaran periode ini "
                   "yang dibayar di bulan Agustus belum terlihat.")
    tgl = kas_terakhir_tgl(data)
    if tgl and data.kas_months and tgl < month_end(max(data.kas_months)) and bulan >= max(data.kas_months).replace(day=1):
        out.append(f"Buku kas baru tercatat s/d {tgl:%d/%m/%Y}; pembayaran sesudah tanggal itu belum terlihat.")
    return out


def periode_pilihan(data):
    """Periode tagihan yang punya data: bulan buku kas sejak Jul 2024 sampai bulan berjalan (terbaru dulu)."""
    out = [m for m in months(data) if m >= KAS_START]
    return list(reversed(out))


def periode_bawaan(data):
    """Periode terbaru yang sudah punya buku kas (biasanya bulan kas terakhir)."""
    kas = [m for m in data.kas_months if m >= KAS_START]
    return kas[-1] if kas else periode_pilihan(data)[0]


def kendali(data, bulan, program=""):
    """Finance Control satu periode tagihan: semua murid aktif (A/B/R) pada periode itu di matriks lifecycle."""
    ms = months(data)
    i = ms.index(bulan) if bulan in ms else len(ms) - 1
    aktif_rows = [b for b in matrix(data) if b.huruf[i] in AKTIF]
    if program:
        aktif_rows = [b for b in aktif_rows if fold(program) in (fold(b.program), fold(b.level).split(" ")[0])]
    rows = [status_bayar(data, b.murid, bulan) for b in aktif_rows]
    kas, _ = kas_per_periode(data)
    per = period_code(bulan)
    diterima_semua = sum(v["total"] for (p, _s), v in kas.items() if p == per)
    ber_tagihan = [r for r in rows if r.tagihan is not None and r.status not in (KEPUTUSAN, TANPA_TAGIHAN)]
    potensi = sum(r.tagihan for r in ber_tagihan)
    tertutup = sum(min(r.bayar, r.tagihan) for r in ber_tagihan)
    hitung = {s: sum(r.status == s for r in rows) for s in (LUNAS, SEBAGIAN, BELUM, MENUNGGU, TANPA_HARGA, TANPA_TAGIHAN, KEPUTUSAN)}
    terlambat = [r for r in rows if r.status in (BELUM, SEBAGIAN, "TERLAMBAT", "BELUM DIBAYAR") and _lewat_tempo(data, bulan)]
    membayar = [r for r in rows if r.bayar > 0]
    return {
        "bulan": bulan, "label": label(bulan), "rows": rows, "aktif": len(rows),
        "sumber": "SPP_TAGIHAN" if bulan >= mulai_v4(data) else "harga SPP × murid aktif (estimasi tagihan)",
        "resmi": bulan >= mulai_v4(data), "keputusan": keputusan_agustus(data, bulan),
        "potensi": potensi, "diterima_aktif": tertutup, "diterima_semua": diterima_semua,
        "outstanding": sum(r.sisa or 0 for r in ber_tagihan),
        "collection": round(tertutup * 100 / potensi, 1) if potensi else None,
        "lunas_pct": round(hitung[LUNAS] * 100 / len(ber_tagihan), 1) if ber_tagihan else None,
        "hitung": hitung, "terlambat": len(terlambat), "terlambat_rp": sum(r.sisa or 0 for r in terlambat),
        "rata_bayar": round(sum(r.bayar for r in membayar) / len(membayar)) if membayar else None,
        "menunggu": _menunggu(data, per), "tak_tertaut": tak_tertaut(data, bulan),
    }


def _lewat_tempo(data, bulan):
    hari = min(28, int(num(float(data.setting("jatuh_tempo", 1) or 1))) or 1)
    return data.today > datetime.date(bulan.year, bulan.month, hari)


def _menunggu(data, per):
    rows = [b for b in BuktiBayar.objects.for_branch(data.branch) if same(b.ver, "Belum Diverifikasi")]
    return {"semua": len(rows), "periode": sum(str(b.per).strip() == per for b in rows),
            "rp": sum(float(b.nominal or 0) for b in rows)}


def tak_tertaut(data, bulan=None):
    """Baris SPP dihitung tanpa murid tertaut (bukan 'BUKAN MURID') - per bulan kas bila `bulan` diberikan."""
    rows = [k for k in kas_rows(data) if same(k.row.jenis, "SPP") and same(k.dihitung, "YA") and not k.s[0]
            and not same(k.row.kor1, BUKAN_MURID) and (bulan is None or as_date(k.row.bulan) == bulan)]
    return {"n": len(rows), "rp": sum(num(k.row.nominal) for k in rows), "baris": rows}


def tren(data, n=12, program=""):
    """Potensi vs diterima per periode tagihan, n periode terakhir yang punya buku kas."""
    out = []
    for bulan in [m for m in data.kas_months if m >= KAS_START][-n:]:
        k = kendali(data, bulan, program)
        out.append({"bulan": bulan, "label": label(bulan), "potensi": k["potensi"], "diterima": k["diterima_aktif"],
                    "outstanding": k["outstanding"], "collection": k["collection"], "keputusan": k["keputusan"]})
    return out


def per_program(k):
    agg = defaultdict(lambda: {"aktif": 0, "potensi": 0.0, "diterima": 0.0, "lunas": 0})
    for r in k["rows"]:
        prog = (r.murid.prog_in or r.murid.program or "(tanpa program)")
        a = agg[prog]
        a["aktif"] += 1
        if r.tagihan is not None and r.status not in (KEPUTUSAN, TANPA_TAGIHAN):
            a["potensi"] += r.tagihan
            a["diterima"] += min(r.bayar, r.tagihan)
        a["lunas"] += r.status == LUNAS
    return sorted(({"program": p, **v, "collection": round(v["diterima"] * 100 / v["potensi"], 1) if v["potensi"] else None}
                   for p, v in agg.items()), key=lambda x: -x["aktif"])


def risiko_murid(data, bulan, k=None, lookback=3):
    """Murid aktif belum lunas periode ini + berapa periode berturut-turut (sampai periode ini) belum ada pembayaran."""
    k = k or kendali(data, bulan)
    ms = [m for m in months(data) if m <= bulan and m >= KAS_START]
    out = []
    for r in k["rows"]:
        if r.status in (LUNAS, TANPA_TAGIHAN, KEPUTUSAN, "DIBEBASKAN"):
            continue
        beruntun = 0
        for m in reversed(ms[-lookback:]):
            s = status_bayar(data, r.murid, m)
            if s.status in (BELUM, "BELUM DIBAYAR", "TERLAMBAT", TANPA_HARGA):
                beruntun += 1
            else:
                break
        kategori = ("Harga belum tercatat" if r.status == TANPA_HARGA else "Belum ada pembayaran" if r.bayar == 0 else
                    "Pembayaran sebagian" if r.status == SEBAGIAN else r.status.capitalize())
        out.append({"r": r, "beruntun": beruntun, "kategori": kategori, "kode": kode_dipakai(r.murid), "guru": guru_dipakai(r.murid)})
    return sorted(out, key=lambda x: (-x["beruntun"], -(x["r"].sisa or 0), fold(x["r"].murid.nama)))


# ------------------------------------------------------------------ Nota SPP

def kepada(data, student):
    """Z10: nama pembayar (PEMBAYAR, Student ID sistem) lalu nama orang tua; bila kosong 'Orang tua / wali <murid>'."""
    p = Pembayar.objects.for_branch(data.branch).filter(std_sys__iexact=student.std).exclude(payer="").order_by("row_no").first()
    if p:
        return p.payer
    if student.par:
        par = ParentMaster.objects.for_branch(data.branch).filter(pid=student.par).first()
        if par and par.nama:
            return par.nama
    return f"Orang tua / wali {student.nama}"


def orang_tua(data, student):
    return ParentMaster.objects.for_branch(data.branch).filter(pid=student.par).first() if student.par else None


def kas_terakhir_tgl(data):
    """Tanggal terakhir di bulan buku kas terakhir (aturan Beranda / HOME Excel: calc.kas.kas_terakhir)."""
    from dashboards.calc.kas import kas_terakhir
    k = kas_terakhir(data)
    return k["tgl"] if k else None


def riwayat_nota(data, student):
    return list(NotaLog.objects.for_branch(data.branch).filter(std__iexact=student.std).order_by("-tgl", "-row_no"))


def awalan_nota(data):
    return str(data.setting("nota_awalan", "") or f"{data.branch.code}/SPP/")
