"""Merakit konteks halaman dasbor dari paket calc (hanya data cabang aktif permintaan ini)."""
from urllib.parse import urlencode

from django.urls import reverse
from django.utils import timezone

from .calc.base import HIST_END, HIST_MONTHS, PERIOD_MONTHS, SEMUA, BranchData, chart, fold, label, parse_period, period_code, short_label
from .calc.beranda import beranda
from .calc.kas import BELUM, KEPUTUSAN, bulanan, ringkasan_spp
from .calc.laporan import STATUS_GRAFIK, Filter, ringkasan_murid
from .calc.operasional import periode_default, periode_v4
from .templatetags.spi import angka, rp

DAFTAR = {"semua": "Semua murid (sesuai filter)", "aktif": "Murid aktif", "status-aktif": "Status Aktif", "baru": "Murid baru",
          "rejoin": "Rejoin", "cuti": "Cuti", "off": "Off", "off-baru": "Off baru", "belum-bayar": "Aktif belum ada pembayaran"}
STATUS_KEY = {"Aktif": "status-aktif", "Baru": "baru", "Rejoin": "rejoin", "Cuti": "cuti", "Off": "off"}
TAMPIL = 30
PERHATIAN = 8


def _pick(value, options):
    v = fold(value)
    return next((o for o in options if fold(o) == v), SEMUA)


def parse_params(data, params):
    months = {period_code(m): m for m in HIST_MONTHS}
    f = Filter(months.get(params.get("bulan", ""), HIST_END), _pick(params.get("program"), data.programs),
               _pick(params.get("tipe"), data.tipes), _pick(params.get("mode"), data.modes), _pick(params.get("guru"), data.gurus))
    daftar = params.get("daftar", "")
    per = parse_period(params.get("periode", ""))
    if per not in PERIOD_MONTHS:
        per = periode_default(data)
        per = per if per in PERIOD_MONTHS else HIST_END
    return f, (daftar if daftar in DAFTAR else ""), per


def _url(f, per, daftar=""):
    q = {"bulan": period_code(f.bulan)}
    q.update({k: v for k, v in (("program", f.program), ("tipe", f.tipe), ("mode", f.mode), ("guru", f.guru)) if v != SEMUA})
    q["periode"] = period_code(per)
    if daftar:
        q["daftar"] = daftar
    return f"{reverse('dashboards:laporan')}?{urlencode(q)}"


def _cocok(key, b, per_baris):
    if key in ("", "semua"):
        return True
    if key == "aktif":
        return b.kelompok == "Aktif"
    if key == "status-aktif":
        return fold(b.status) == "aktif"
    if key in ("baru", "rejoin"):
        return fold(b.status) == key
    if key in ("cuti", "off"):
        return fold(b.kelompok) == key
    if key == "off-baru":
        return b.off_baru
    return per_baris[id(b.murid)][1] == BELUM                         # belum-bayar


def _card(tone, icon, label, value, sub, hx=None, soon=False):
    return {"tone": tone, "icon": icon, "label": label, "value": value, "sub": sub, "hx": hx, "soon": soon}


def _perhatian(judul, ikon, rows, kolom, url, catatan=""):
    n = len(rows)
    teks = catatan or (f"menampilkan {PERHATIAN} dari {n}" if n > PERHATIAN else f"total: {n}")
    return {"judul": judul, "ikon": ikon, "rows": [[getattr(b, k) or "—" for k in kolom] for b in rows[:PERHATIAN]], "catatan": teks,
            "url": url if n else None}


def laporan_context(request):
    data = branch_data(request)
    f, daftar_key, per = parse_params(data, request.GET)
    m, s = ringkasan_murid(data, f), ringkasan_spp(data, f)
    u = lambda key="": _url(f, per, key)  # noqa: E731
    murid_cards = [
        _card("murid", "users", "Total data murid", angka(m["murid"][0]), "Aktif + Cuti (tanpa Off)", u("semua")),
        _card("murid", "user-check", "Murid aktif", angka(m["murid"][1]), "Aktif + Baru + Rejoin", u("aktif")),
        _card("akad", "user-plus", "Murid baru", angka(m["murid"][2]), "status 'Baru' bulan ini", u("baru")),
        _card("kelas", "arrow-back-up", "Rejoin", angka(m["murid"][3]), "kembali dari cuti/off", u("rejoin")),
        _card("off", "player-pause", "Cuti", angka(m["murid"][4]), "status 'Cuti' bulan ini", u("cuti")),
        _card("kritis", "user-off", "Off (status bulan ini)", angka(m["murid"][5]), "seluruh murid berstatus Off", u("off")),
        _card("kritis", "user-minus", "Off baru", angka(m["murid"][6]), "baru Off dibanding bulan lalu", u("off-baru")),
        _card("soon", "chart-line", "Retensi", "TIDAK TERSEDIA", "belum ada definisi retensi di data sumber (lihat PANDUAN)"),
    ]
    v = s["spp"]
    spp_cards = [
        _card("spp", "cash", "SPP diterima (Rp)", rp(v[0]), "buku kas bulan terpilih · semua murid"),
        _card("spp", "calendar-dollar", "SPP tahun ini s/d bulan ini (Rp)", rp(v[1]), "Januari sampai bulan terpilih"),
        _card("murid", "users", "Murid aktif", angka(v[2]), "sesuai filter", u("aktif")),
        _card("spp", "circle-check", "Aktif sudah bayar", angka(v[3]), "ada penerimaan di buku kas"),
        _card("off", "hourglass", "Aktif belum ada pembayaran", angka(v[4]), "bukan tunggakan: belum tercatat di buku kas",
              u("belum-bayar") if isinstance(v[4], int) and v[4] else None),
        _card("kritis", "link-off", "Penerimaan belum tertaut", angka(v[5]), "baris SPP tanpa nama murid jelas"),
        _card("akad", "zoom-question", "Tautan lemah (cek)", angka(v[6]), "semua bulan · mohon dicek di BUKU_KAS"),
        _card("soon", "user-question", "Nama menunggu", "", "butuh data CEK NAMA (menyusul)", soon=True),
    ]
    kas = bulanan(data)
    bayar_note = "belum ada buku kas" if v[3] == "—" else KEPUTUSAN if s["keputusan"] else ""
    sudah = int(str(v[3]).split()[0]) if isinstance(v[3], str) and v[3][:1].isdigit() else 0
    charts = [
        chart("c-tren", "Tren murid 33 bulan", [t[0] for t in m["tren"]],
              [("Aktif", [t[1] for t in m["tren"]]), ("Cuti", [t[2] for t in m["tren"]]), ("Off", [t[3] for t in m["tren"]]),
               ("Baru", [t[4] for t in m["tren"]])], type="line", note="semua murid DB Murid · filter selain bulan"),
        chart("c-status", "Status murid bulan ini", STATUS_GRAFIK, [("Murid", [n for _l, n in m["status"]])],
              links=[u(STATUS_KEY[x]) for x in STATUS_GRAFIK], note="klik batang untuk melihat daftarnya"),
        chart("c-level", "Murid aktif per level", [x[0] for x in m["level"]], [("Murid aktif", [x[1] for x in m["level"]])],
              horizontal=True, height="h-96"),
        chart("c-tipe", "Murid aktif per tipe kelas", [x[0] for x in m["tipe"]], [("Murid aktif", [x[1] for x in m["tipe"]])]),
        chart("c-guru", "Murid aktif per guru (10 teratas)", [x[0] for x in m["guru"]], [("Murid aktif", [x[1] for x in m["guru"]])],
              horizontal=True, height="h-96"),
        chart("c-kas", "SPP diterima per bulan (buku kas)", [short_label(k[0]) for k in kas],
              [("Tertaut ke murid", [k[2] for k in kas]), ("Belum tertaut", [k[3] for k in kas])], stacked=True, money=True,
              note="semua murid · Jenis SPP, Dihitung YA"),
        chart("c-bayar", "Status pembayaran murid aktif", ["Sudah ada pembayaran", "Belum ada pembayaran"],
              [("Murid", [sudah, v[4] if isinstance(v[4], int) else 0])], links=[None, u("belum-bayar")], note=bayar_note),
    ]
    catatan_bayar = "Agustus 2026: perlu keputusan jurnal (SETTINGS)" if s["keputusan"] else ""
    perhatian = [
        _perhatian("Murid baru", "user-plus", m["baru"], ("nama", "level"), u("baru")),
        _perhatian("Off baru", "user-minus", m["off_baru"], ("nama", "level"), u("off-baru")),
        _perhatian("Aktif belum ada pembayaran", "hourglass", s["belum_bayar"], ("nama", "guru", "tipe"), u("belum-bayar"), catatan_bayar),
    ]
    semua = [b for b in m["daftar"] if _cocok(daftar_key, b, s["per_baris"])]
    tampil = semua if daftar_key else semua[:TAMPIL]
    daftar = {"key": daftar_key, "judul": DAFTAR.get(daftar_key, "Daftar murid"), "total": len(semua), "lebih": len(semua) > len(tampil),
              "semua_url": u("semua"), "reset_url": u(),
              "rows": [{"nama": b.nama, "status": b.status, "program": b.program, "level": b.level, "kode": b.kode_kelas, "guru": b.guru,
                        "tipe": b.tipe, "mode": b.mode, "spp": s["per_baris"][id(b.murid)][0], "bayar": s["per_baris"][id(b.murid)][1],
                        "std": b.std} for b in tampil]}
    v4 = periode_v4(data, per)
    label_filter = label(f.bulan) + "".join(f"  ·  {x}" for x in (f.program, f.tipe, f.mode) if x != SEMUA) + \
        (f"  ·  {f.guru}" if f.guru != SEMUA else "  ·  semua guru")
    return {
        "f": f, "filter_label": label_filter, "periode": per, "periode_kode": period_code(per),
        "opsi": {"bulan": [(period_code(x), label(x)) for x in reversed(HIST_MONTHS)], "program": data.programs, "tipe": data.tipes,
                 "mode": data.modes, "guru": data.gurus, "periode": [(period_code(x), label(x)) for x in PERIOD_MONTHS]},
        "bulan_kode": period_code(f.bulan),
        "murid_cards": murid_cards, "spp_cards": spp_cards, "charts": charts, "perhatian": perhatian, "daftar": daftar,
        "v4": {"status": list(zip(["ACTIVE", "ON LEAVE", "OFF", "PENDING"], v4["status"])),
               "aktivitas": list(zip(["Murid masuk", "OFF baru", "Cuti baru", "Aktif kembali", "Sesi terlaksana", "Sesi batal", "Lead baru",
                                      "Follow-up", "Catatan akademik"], v4["aktivitas"]))},
        "kosong": not data.d_murid,
    }


def branch_data(request):
    return BranchData(request.branch, timezone.localdate())


def beranda_context(request):
    h = beranda(branch_data(request))
    spp_label = f"SPP diterima {label(h['spp_bulan'])} (Rp)" if h["spp_bulan"] else "SPP diterima (Rp)"
    return {"h": h, "spp_label": spp_label}
