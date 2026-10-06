"""Operational Health: sesi, kehadiran, kelas, guru, follow-up - dari tabel operasional yang sama dengan halaman Sesi/Kelas/Guru."""
import datetime
from collections import Counter

from classes.models import ClassSchedule, Kehadiran
from classes.services import attendance_rate
from dashboards.calc.base import as_date, fold, period_code, same
from dashboards.calc.kelas import daftar_kelas
from masterdata.services import teacher_rows
from students.services import due_bucket, is_open_followup

DONE = ("REALIZED", "MAKE-UP")


def _done(s):
    return fold(s.status) in ("realized", "make-up")


def operasional(data, bulan):
    today = data.today
    per = period_code(bulan)
    sesi_bulan = [s for s in data.sesi if same(s.per, per) or (as_date(s.tgl) and as_date(s.tgl).replace(day=1) == bulan and not s.per)]
    realisasi = [s for s in sesi_bulan if _done(s)]
    hadir_sid = Counter(Kehadiran.objects.filter(branch=data.branch, sid__in=[s.sid for s in realisasi]).values_list("sid", flat=True))
    tanpa_absen = [s for s in realisasi if not hadir_sid[s.sid]]
    lampau = [s for s in data.sesi if same(s.status, "SCHEDULED") and as_date(s.tgl) and as_date(s.tgl) < today]
    since = today - datetime.timedelta(days=30)
    sids_30 = [s.sid for s in data.sesi if as_date(s.tgl) and since <= as_date(s.tgl) <= today]

    kelas = daftar_kelas(data)
    jadwal = Counter(fold(sc.code) for sc in ClassSchedule.objects.for_branch(data.branch).only("code", "eff_until") if sc.code)
    aktif_k = [k for k in kelas if k.status_kelas == "ACTIVE"]
    dengan_kap = [k for k in aktif_k if isinstance(k.kapasitas, (int, float)) and k.kapasitas]
    kursi, terisi = sum(k.kapasitas for k in dengan_kap), sum(k.aktif for k in dengan_kap)
    terjadwal_kosong = [k for k in kelas if k.status_kelas != "ACTIVE" and jadwal[fold(k.row.code)]]

    guru = [g for g in teacher_rows(data.branch, today) if fold(g["t"].status) == "active" or g["aktif"]]
    beban = [g["aktif"] for g in guru if g["aktif"]]
    rata = round(sum(beban) / len(beban), 1) if beban else 0
    for g in guru:
        g["rasio"] = round(g["aktif"] / rata, 2) if rata else None
        g["catatan"] = ("tanpa murid aktif" if g["aktif"] == 0 else "beban tinggi (≥ 1,5× rata-rata)" if rata and g["aktif"] >= 1.5 * rata
                        else "beban rendah (≤ 0,5× rata-rata)" if rata and g["aktif"] <= 0.5 * rata else "")

    fu = [f for f in data.followups if is_open_followup(f)]
    fu_b = Counter(due_bucket(as_date(f.next), today) for f in fu)

    return {
        "bulan": bulan,
        "sesi": {"hari_ini": sum(as_date(s.tgl) == today for s in data.sesi), "bulan": len(sesi_bulan), "realisasi": len(realisasi),
                 "terjadwal": sum(same(s.status, "SCHEDULED") for s in sesi_bulan), "batal": sum(same(s.status, "CANCELLED") for s in sesi_bulan),
                 "lampau_belum": len(lampau), "lampau": sorted(lampau, key=lambda s: (as_date(s.tgl), s.mulai or datetime.time())),
                 "absen_lengkap": len(realisasi) - len(tanpa_absen), "tanpa_absen": tanpa_absen,
                 "absen_pct": round((len(realisasi) - len(tanpa_absen)) * 100 / len(realisasi), 1) if realisasi else None,
                 "konfirmasi_pct": _pct(sum(_done(s) or same(s.status, "CANCELLED") for s in data.sesi if as_date(s.tgl) and as_date(s.tgl) < today),
                                        sum(1 for s in data.sesi if as_date(s.tgl) and as_date(s.tgl) < today))},
        "kehadiran": attendance_rate(data.branch, sids=sids_30),
        "kelas": {"aktif": len(aktif_k), "penuh": sum(k.status_kapasitas == "FULL" for k in kelas),
                  "melebihi": [k for k in kelas if k.status_kapasitas == "OVER CAPACITY"],
                  "kosong_terjadwal": terjadwal_kosong, "kursi": int(kursi), "terisi": int(terisi),
                  "kursi_kosong": int(sum(k.kursi_kosong for k in kelas)), "util": _pct(terisi, kursi),
                  "tanpa_guru": [k for k in aktif_k if not (k.row.guru or "").strip()],
                  "tanpa_jadwal": [k for k in aktif_k if not jadwal[fold(k.row.code)]]},
        "guru": sorted(guru, key=lambda g: -g["aktif"]), "rata_beban": rata,
        "followup": {"terbuka": len(fu), "terlambat": fu_b["TERLAMBAT"], "hari_ini": fu_b["HARI INI"], "minggu": fu_b["MINGGU INI"],
                     "tanpa_tanggal": fu_b["TANPA TANGGAL"]},
    }


def _pct(a, b):
    return round(a * 100 / b, 1) if b else None
