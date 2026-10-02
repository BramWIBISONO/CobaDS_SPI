"""Masalah kritis, bukti bayar, periode operasional v4 (spesifikasi §3.7)."""
from .base import BELUM_DIPUTUSKAN, as_date, fold, parse_period, period_code, same
from .status import status_akhir_periode

STATUS_V4 = ["ACTIVE", "ON LEAVE", "OFF", "PENDING"]


def kritis(data):
    return sum(1 for i in data.issues if same(i.sev, "CRITICAL") and not same(i.status, "RESOLVED")
               and not same(i.status, "CLOSED") and not same(i.still, "CLEARED"))


def teks_kritis(data, n):
    if same(data.setting("jurnal_agu", ""), BELUM_DIPUTUSKAN):
        return "Jurnal Agustus 2026 perlu keputusan (SETTINGS)"
    return "tidak ada masalah kritis terbuka" if n == 0 else "lihat TINDAKAN bagian 0"


def bukti(data):
    belum = sum(1 for b in data.bukti if same(b.ver, "Belum Diverifikasi"))
    cek = sum(1 for b in data.bukti if same(b.ver, "Tidak Cocok") or same(b.ver, "Perlu Klarifikasi"))
    return belum, cek


def _per(tgl):
    d = as_date(tgl)
    return period_code(d) if d else ""


def periode_default(data):
    return data.period_open or data.bulan_ini


def periode_v4(data, mulai):
    kode = period_code(mulai)
    baris = {s.std: status_akhir_periode(data, s, mulai) for s in data.students if s.std}
    ev = [e for e in data.events if _per(e.tgl) == kode]
    sesi = [s for s in data.sesi if same(s.per, kode)]
    return {
        "status": [sum(same(v, s) for v in baris.values()) for s in STATUS_V4],
        "aktivitas": [
            sum(same(e.jenis, "MASUK") for e in ev), sum(same(e.status, "OFF") for e in ev),
            sum(same(e.status, "ON LEAVE") for e in ev), sum(fold(e.jenis).startswith("aktif kembali") for e in ev),
            sum(same(s.status, "REALIZED") or same(s.status, "MAKE-UP") for s in sesi), sum(same(s.status, "CANCELLED") for s in sesi),
            sum(_per(x.tgl) == kode for x in data.leads), sum(_per(x.tgl) == kode for x in data.followups),
            sum(_per(x.tgl) == kode for x in data.academics)],
        "baris": baris,
    }
