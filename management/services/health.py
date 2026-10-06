"""Skor kesehatan (0-100) & keputusan manajemen - aturan transparan, satu tempat.

Setiap komponen memetakan satu angka nyata ke 0-100 secara linear antara ambang 'buruk' (0) dan 'baik' (100).
Komponen tanpa data tidak dihitung (ditandai). Skor dimensi = rata-rata komponennya; Business Health = rata-rata tertimbang dimensi.
Ambang adalah pilihan manajemen awal (bukan dari Excel) dan ditampilkan di halaman Business Health.
"""
from django.urls import reverse

from dashboards.calc.base import label, same
from dashboards.calc.operasional import kritis

from . import data_health, finance, lifecycle, operations

STATUS = [(80, "Sehat", "st-baik"), (65, "Pantau", "st-perhatian"), (50, "Berisiko", "st-serius"), (0, "Kritis", "st-kritis")]
BOBOT_BISNIS = {"student": 30, "financial": 30, "operational": 20, "data": 20}
NAMA = {"student": "Student Health", "financial": "Financial Health", "operational": "Operational Health", "data": "Data Health"}

# (kunci, nama, satuan, buruk, baik, arti) - nilai di antara buruk & baik dipetakan linear ke 0-100
AMBANG = {
    "retensi": ("Retensi bulanan", "%", 85, 98, "murid basis bulan lalu yang masih aktif/cuti"),
    "pertumbuhan": ("Pertumbuhan murid aktif 3 bulan", "%", -10, 3, "perubahan murid aktif vs 3 bulan sebelumnya"),
    "net": ("Murid baru + rejoin dikurangi Off baru", "murid", -10, 5, "per bulan"),
    "collection": ("Collection SPP periode", "%", 60, 95, "pembayaran tercatat ÷ tagihan (estimasi harga SPP sebelum Okt 2026)"),
    "lunas": ("Murid aktif lunas", "%", 50, 90, "murid aktif berstatus LUNAS periode itu"),
    "tertaut": ("Penerimaan SPP tertaut ke murid", "%", 90, 100, "baris SPP buku kas bulan itu yang tertaut ke murid"),
    "konfirmasi": ("Sesi lampau terkonfirmasi", "%", 50, 100, "sesi sebelum hari ini yang sudah terlaksana / batal"),
    "absensi": ("Sesi terlaksana dengan absensi", "%", 50, 100, "bulan berjalan"),
    "followup": ("Follow-up tidak terlambat", "%", 50, 100, "follow-up terbuka yang belum lewat tanggal"),
    "util": ("Keterisian kursi kelas aktif", "%", 40, 85, "murid aktif ÷ kapasitas kelas Partner & Group"),
    "data": ("Skor Data Health", "", 0, 100, "sudah 0-100 - lihat halaman Data Health"),
}


def peta(key, nilai):
    if nilai is None:
        return None
    _n, _u, buruk, baik, _a = AMBANG[key]
    return max(0, min(100, round((nilai - buruk) * 100 / (baik - buruk))))


def status_skor(skor):
    if skor is None:
        return ("Tidak cukup data", "st-netral")
    for batas, nama, nada in STATUS:
        if skor >= batas:
            return (nama, nada)


def _komponen(key, nilai, sumber):
    n, u, buruk, baik, arti = AMBANG[key]
    return {"key": key, "nama": n, "nilai": nilai, "satuan": u, "skor": peta(key, nilai), "buruk": buruk, "baik": baik, "arti": arti, "sumber": sumber}


def _dimensi(key, komponen):
    ada = [k["skor"] for k in komponen if k["skor"] is not None]
    skor = round(sum(ada) / len(ada)) if ada else None
    st, nada = status_skor(skor)
    return {"key": key, "nama": NAMA[key], "skor": skor, "status": st, "nada": nada, "komponen": komponen}


def ringkasan(data, bulan=None, program="", guru=""):
    """Semua angka manajemen untuk satu periode (bawaan bulan berjalan untuk murid; periode kas terakhir untuk keuangan)."""
    ms = lifecycle.months(data)
    bulan = bulan if bulan in ms else ms[-1]
    i = ms.index(bulan)
    rows = lifecycle.filtered(lifecycle.matrix(data), program=program, guru=guru)
    ser = lifecycle.series(data, rows)
    cur, prev = ser[i], ser[i - 1] if i else None
    tiga = ser[i - 3] if i >= 3 else None
    tahun = ser[i - 12] if i >= 12 else None
    tumbuh = round((cur["aktif"] - tiga["aktif"]) * 100 / tiga["aktif"], 1) if tiga and tiga["aktif"] else None
    net = (cur["baru"] + cur["rejoin"] - (cur["off_baru"] or 0)) if prev else None

    per_kas = finance.periode_bawaan(data) if bulan >= finance.mulai_v4(data) or bulan not in data.kas_months else bulan
    k = finance.kendali(data, per_kas, program)
    tak = finance.tak_tertaut(data, per_kas)
    spp_rows = sum(1 for kr in finance.kas_rows(data) if same(kr.row.jenis, "SPP") and same(kr.dihitung, "YA") and kr.row.bulan and kr.row.bulan == per_kas)
    tertaut = round((spp_rows - tak["n"]) * 100 / spp_rows, 1) if spp_rows else None

    op = operations.operasional(data, bulan)
    fu = op["followup"]
    cek = data_health.cek_semua(data)
    dskor = data_health.skor(cek)

    dims = [
        _dimensi("student", [_komponen("retensi", cur["retensi"], "Student Lifecycle"),
                             _komponen("pertumbuhan", tumbuh, "Student Lifecycle"), _komponen("net", net, "Student Lifecycle")]),
        _dimensi("financial", [_komponen("collection", k["collection"], f"Finance Control {k['label']}"),
                               _komponen("lunas", k["lunas_pct"], f"Finance Control {k['label']}"),
                               _komponen("tertaut", tertaut, f"BUKU_KAS {label(per_kas)}")]),
        _dimensi("operational", [_komponen("konfirmasi", op["sesi"]["konfirmasi_pct"], "SESI"),
                                 _komponen("absensi", op["sesi"]["absen_pct"], "SESI + KEHADIRAN"),
                                 _komponen("followup", round((fu["terbuka"] - fu["terlambat"]) * 100 / fu["terbuka"], 1) if fu["terbuka"] else None, "FOLLOW_UP"),
                                 _komponen("util", op["kelas"]["util"], "CLASS_MASTER")]),
        _dimensi("data", [_komponen("data", dskor, "Data Health")]),
    ]
    ada = [d for d in dims if d["skor"] is not None]
    w = sum(BOBOT_BISNIS[d["key"]] for d in ada)
    bisnis = round(sum(d["skor"] * BOBOT_BISNIS[d["key"]] for d in ada) / w) if w else None
    st, nada = status_skor(bisnis)
    catatan_kas = finance.catatan_kas(data, per_kas)
    return {"catatan_kas": catatan_kas, "bulan": bulan, "i": i, "series": ser, "cur": cur, "prev": prev, "tiga": tiga, "tahun": tahun, "tumbuh": tumbuh, "net": net,
            "kas": k, "per_kas": per_kas, "tak_tertaut": tak, "tertaut": tertaut, "op": op, "cek": cek, "data_skor": dskor,
            "dimensi": dims, "bisnis": {"skor": bisnis, "status": st, "nada": nada}, "rows": rows}


def _tren(cur, prev, naik_baik=True):
    if cur is None or prev is None:
        return None
    if cur == prev:
        return {"arah": "tetap", "ikon": "minus", "baik": None, "beda": 0}
    naik = cur > prev
    return {"arah": "naik" if naik else "turun", "ikon": "trending-up" if naik else "trending-down", "baik": naik == naik_baik,
            "beda": round(cur - prev, 1)}


def keputusan(data, r, perms):
    """Daftar 'yang membutuhkan perhatian' - hanya muncul bila angkanya nyata. Diurutkan: Kritis, Perlu Keputusan, Follow-up, Data, Positif."""
    out = []
    upd = data.last_import.date if data.last_import else None
    cur, prev = r["cur"], r["prev"]

    def add(kat, isu, dampak, metrik, nilai, sebelum, tren, jumlah, aksi, url, modul, ambang="", sebab=""):
        out.append({"kat": kat, "isu": isu, "dampak": dampak, "metrik": metrik, "nilai": nilai, "sebelum": sebelum, "tren": tren,
                    "jumlah": jumlah, "aksi": aksi, "url": url, "modul": modul, "ambang": ambang, "sebab": sebab, "update": upd})

    lc = reverse("management:lifecycle")
    if same(data.setting("jurnal_agu", ""), "BELUM DIPUTUSKAN"):
        add("Perlu Keputusan", "Jurnal penerimaan Agustus 2026 belum diputuskan", "SPP Agustus 2026 tidak bisa dihitung, ditagih, maupun dibuatkan nota.",
            "Setting jurnal_agu", "BELUM DIPUTUSKAN", "", None, 1, "Putuskan versi jurnal yang dipakai (tersembunyi atau revisi).", "", "Pengaturan cabang",
            sebab="Dua versi jurnal Agustus 2026 di buku kas.")
    n_kritis = kritis(data)
    if n_kritis:
        add("Kritis", f"{n_kritis} isu data kritis terbuka", "Angka laporan yang bergantung pada data ini bisa salah.", "ISSUE_UNIT CRITICAL",
            n_kritis, "", None, n_kritis, "Tinjau isu kritis di Data Health.", reverse("management:data") + "#isu_kritis", "Data Health")
    if prev and cur["off_baru"] and prev["off_baru"] is not None and cur["off_baru"] > prev["off_baru"] and cur["off_baru"] >= 3:
        add("Kritis", f"Off baru naik: {cur['off_baru']} murid ({cur['label']})", "Risiko churn meningkat.", "Off baru",
            cur["off_baru"], prev["off_baru"], _tren(cur["off_baru"], prev["off_baru"], False), cur["off_baru"],
            "Tinjau murid baru Off dan buka follow-up.", lc + "?status=O", "Student Lifecycle", sebab="Lihat alasan OFF per murid.")
    elif cur["off_baru"]:
        add("Perlu Follow-up", f"{cur['off_baru']} murid baru menjadi Off ({cur['label']})", "Murid yang baru Off paling mungkin diajak kembali.",
            "Off baru", cur["off_baru"], prev["off_baru"] if prev else None, _tren(cur["off_baru"], prev["off_baru"] if prev else None, False),
            cur["off_baru"], "Hubungi orang tua & catat follow-up.", lc + "?status=O", "Student Lifecycle")
    if cur["hilang"]:
        add("Data Issue", f"{cur['hilang']} murid hilang dari catatan status ({cur['label']})",
            "Bulan lalu aktif/cuti, bulan ini tanpa status - angka retensi tidak lengkap.", "Hilang dari catatan", cur["hilang"], "", None,
            cur["hilang"], "Lengkapi status murid di matriks lifecycle.", lc + "?status=%3F", "Student Lifecycle")
    k = r["kas"]
    if "management.finance" in perms and not k["keputusan"] and not k["resmi"]:
        belum = k["hitung"][finance.BELUM] + k["hitung"][finance.SEBAGIAN]
        if belum:
            add("Perlu Follow-up", f"{belum} murid aktif belum lunas SPP {k['label']}", "Pendapatan periode ini belum tertagih penuh.",
                "Collection (estimasi)", f"{k['collection']}%" if k["collection"] is not None else "-", "", None, belum,
                "Tinjau daftar risiko pembayaran dan kirim nota.", reverse("management:finance") + f"?periode={k['bulan']:%Y-%m}#risiko",
                "Finance Control", ambang="≥ 95% sehat", sebab=" ".join(r["catatan_kas"]) or "Belum ada pembayaran tercatat di buku kas.")
        if k["hitung"][finance.TANPA_HARGA]:
            n = k["hitung"][finance.TANPA_HARGA]
            add("Data Issue", f"{n} murid aktif tanpa harga SPP", "Tagihan & nota murid ini tidak bisa dihitung.", "Harga SPP kosong", n, "", None, n,
                "Isi harga SPP di profil murid.", reverse("management:data") + "#murid_tanpa_harga", "Data Health")
    if r["tak_tertaut"]["n"]:
        add("Data Issue", f"{r['tak_tertaut']['n']} penerimaan SPP belum tertaut ke murid ({label(r['per_kas'])})",
            "Uang masuk tidak tercatat sebagai pembayaran murid mana pun.", "Baris kas tak tertaut", r["tak_tertaut"]["n"], "", None,
            r["tak_tertaut"]["n"], "Isi 'Murid (koreksi)' pada baris buku kas.", reverse("management:data") + "#kas_tak_tertaut", "Data Health")
    op = r["op"]
    if op["sesi"]["lampau_belum"]:
        add("Perlu Follow-up", f"{op['sesi']['lampau_belum']} sesi lampau belum dikonfirmasi", "Kehadiran & realisasi mengajar belum lengkap.",
            "Sesi SCHEDULED < hari ini", op["sesi"]["lampau_belum"], "", None, op["sesi"]["lampau_belum"], "Konfirmasi sesi dan isi absensi.",
            reverse("classes:sessions") + "?tampilan=tertunda", "Sesi & Kehadiran")
    if op["kelas"]["melebihi"]:
        n = len(op["kelas"]["melebihi"])
        add("Kritis", f"{n} kelas melebihi kapasitas", "Kualitas kelas & kepuasan orang tua terancam.", "Kelas OVER CAPACITY", n, "", None, n,
            "Pecah kelas atau pindahkan murid.", reverse("management:operations") + "#kelas", "Operational Health")
    kosong = op["kelas"]["kosong_terjadwal"]
    if kosong:
        add("Perlu Keputusan", f"{len(kosong)} kelas masih terjadwal tanpa murid aktif", "Slot guru & ruang terpakai tanpa pendapatan.",
            "Kelas tanpa murid aktif + jadwal", len(kosong), "", None, len(kosong), "Tutup jadwal kelas atau isi dengan murid baru.",
            reverse("management:operations") + "#kelas", "Operational Health")
    if op["followup"]["terlambat"]:
        n = op["followup"]["terlambat"]
        add("Perlu Follow-up", f"{n} follow-up lewat tanggal", "Tindak lanjut ke orang tua tertunda.", "Follow-up terlambat", n, "", None, n,
            "Kerjakan follow-up terlambat.", reverse("students:followups"), "Follow-up")
    if prev and cur["aktif"] > prev["aktif"]:
        add("Positive Trend", f"Murid aktif naik menjadi {cur['aktif']}", "Basis pendapatan bertambah.", "Murid aktif", cur["aktif"], prev["aktif"],
            _tren(cur["aktif"], prev["aktif"]), cur["aktif"] - prev["aktif"], "Pertahankan; pastikan kapasitas kelas cukup.", lc, "Student Lifecycle")
    if prev and cur["rejoin"]:
        add("Positive Trend", f"{cur['rejoin']} murid kembali (rejoin) {cur['label']}", "Reaktivasi berjalan.", "Rejoin", cur["rejoin"],
            prev["rejoin"], _tren(cur["rejoin"], prev["rejoin"]), cur["rejoin"], "Catat apa yang membuat mereka kembali.", lc + "?status=R", "Student Lifecycle")
    urut = {"Kritis": 0, "Perlu Keputusan": 1, "Perlu Follow-up": 2, "Data Issue": 3, "Positive Trend": 4}
    return sorted(out, key=lambda x: urut[x["kat"]])


KATEGORI_NADA = {"Kritis": "st-kritis", "Perlu Keputusan": "st-serius", "Perlu Follow-up": "st-perhatian", "Data Issue": "st-info",
                 "Positive Trend": "st-baik"}
