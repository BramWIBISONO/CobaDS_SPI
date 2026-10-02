"""Ringkasan HOME (spesifikasi §4 Beranda) — teks keterangan sama dengan rumus HOME Excel."""
from collections import Counter

from .base import HIST_END, day_label, fixed, fold, label, month_end, same
from .kas import kas_terakhir
from .kelas import ringkasan_kelas
from .off import ringkasan_off
from .operasional import bukti, kritis, teks_kritis
from .status import guru_dipakai, kode_dipakai, semua_status_sekarang

SEP = "  ·  "
SEP_JUDUL = "   ·   "


def _periode_label(data):
    row = next((p for p in data.periodes if same(p.status, "OPEN")), None)
    return (row.label or "-") if row else "-"


def beranda(data):
    st = semua_status_sekarang(data)
    n = Counter(fold(st[fold(s.std)]) for s in data.students if s.std)
    kas = kas_terakhir(data)
    off, kelas = ringkasan_off(data), ringkasan_kelas(data)
    n_kritis = kritis(data)
    belum, cek = bukti(data)
    if kas is None:
        sub_spp, kas_judul = "buku kas belum ada", "buku kas —"
    else:
        tgl = day_label(kas["tgl"]) if kas["tgl"] else label(kas["bulan"])
        lengkap = "" if kas["tgl"] and kas["tgl"] >= month_end(kas["bulan"]) else " (belum lengkap)"
        sub_spp = f"buku kas s/d {tgl}{lengkap}"
        if kas["prev_bulan"]:
            sub_spp += f"{SEP}{label(kas['prev_bulan'])}: Rp {fixed(kas['prev_total'])}"
        kas_judul = f"buku kas s/d {tgl}"
    riwayat = f"riwayat DB Murid s/d {label(HIST_END)}" if data.d_bulan else "riwayat DB Murid —"
    periode = _periode_label(data)
    return {
        "judul": f"Periode berjalan: {periode}{SEP_JUDUL}{riwayat}{SEP_JUDUL}{kas_judul}",
        "periode": periode,
        "aktif": n["active"],
        "sub_aktif": f"cuti {n['on leave']}{SEP}pending {n['pending']}{SEP}status v4 (INPUT CENTER)",
        "spp": kas["total"] if kas else None,
        "spp_bulan": kas["bulan"] if kas else None,
        "sub_spp": sub_spp,
        "off": off["masih"],
        "sub_off": f"{off['perlu']} perlu follow-up{SEP}baru Off {label(data.bulan_ini)}: {off['baru']}",
        "off_raw": [off["baru"], off["masih"], off["perlu"]],
        "kelas": kelas["aktif"],
        "sub_kelas": f"penuh {kelas['penuh']}{SEP}kursi kosong {fixed(kelas['kursi'])}{SEP}melebihi {kelas['melebihi']}",
        "kelas_raw": [kelas["kursi"], kelas["aktif"]],
        "kritis": n_kritis,
        "sub_kritis": teks_kritis(data, n_kritis),
        "bukti": belum,
        "sub_bukti": f"bukti bayar dari INPUT CENTER{SEP}perlu klarifikasi: {cek}",
        "impor": data.last_import,
    }


def cari_murid(data, q, limit=20):
    q = fold(q).strip()
    if not q:
        return []
    st = semua_status_sekarang(data)
    out = []
    for s in data.students:
        if s.std and q in fold(s.nama):
            out.append({"nama": s.nama or "", "status": st[fold(s.std)], "kode": kode_dipakai(s), "guru": guru_dipakai(s), "std": s.std})
            if len(out) >= limit:
                break
    return out
