"""Data Health: kelengkapan & kerapian data cabang. Setiap cek menyimpan catatan yang terkena (bisa dibuka satu per satu).

Skor 0-100 = rata-rata tertimbang (1 - terkena ÷ diperiksa) per cek; bobot menurut tingkat: kritis 3 · tinggi 2 · sedang 1,5 · rendah 1.
Cek yang tidak punya data untuk diperiksa (diperiksa = 0) tidak ikut dihitung.
"""
import re
from collections import defaultdict
from dataclasses import dataclass, field

from django.urls import reverse

from classes.models import ClassSchedule, Kehadiran
from dashboards.calc.base import KAS_START, as_date, fold, same
from dashboards.calc.kas import BUKAN_MURID, kas_rows
from dashboards.calc.kelas import daftar_kelas
from dashboards.calc.status import guru_dipakai, kode_dipakai, semua_status_sekarang
from finance.models import BuktiBayar
from masterdata.services import teacher_key
from students.models import ParentMaster

from .finance import harga_dipakai

BOBOT = {"kritis": 3.0, "tinggi": 2.0, "sedang": 1.5, "rendah": 1.0}
NADA = {"kritis": "st-kritis", "tinggi": "st-serius", "sedang": "st-perhatian", "rendah": "st-netral"}
TAMPIL = 50


@dataclass
class Cek:
    key: str
    kategori: str
    judul: str
    tingkat: str
    diperiksa: int
    terkena: list = field(default_factory=list)          # [{'label', 'detail', 'url'}]
    aksi: str = ""
    sumber: str = ""

    @property
    def n(self):
        return len(self.terkena)

    @property
    def skor(self):
        return None if not self.diperiksa else round((1 - self.n / self.diperiksa) * 100, 1)

    @property
    def nada(self):
        return NADA[self.tingkat] if self.n else "st-baik"


def _murid(s, detail=""):
    return {"label": s.nama or s.std, "detail": detail or s.std, "url": reverse("students:detail", args=[s.std])}


def _digits(v):
    d = re.sub(r"\D", "", str(v or ""))
    return "62" + d[1:] if d.startswith("0") else d


def cek_semua(data):
    def build():
        st = semua_status_sekarang(data)
        semua = [s for s in data.students if s.std]
        aktif = [s for s in semua if fold(st.get(fold(s.std))) == "active"]
        parents = {p.pid: p for p in ParentMaster.objects.for_branch(data.branch)}
        punya_riwayat = {fold(r.v1) for r in data.d_bulan if r.v1}
        punya_event = set(data.events_by_std)
        guru_dikenal = {teacher_key(t.name) for t in data.teachers if t.name}
        kelas = daftar_kelas(data)
        aktif_k = [k for k in kelas if k.status_kelas == "ACTIVE"]
        jadwal = {fold(sc.code) for sc in ClassSchedule.objects.for_branch(data.branch).only("code") if sc.code}
        out = []

        def add(key, kat, judul, tingkat, diperiksa, terkena, aksi, sumber):
            out.append(Cek(key, kat, judul, tingkat, diperiksa, terkena, aksi, sumber))

        # ---- Data murid
        add("murid_tanpa_ortu", "Data murid", "Murid aktif tanpa orang tua", "tinggi", len(aktif),
            [_murid(s, f"Parent ID: {s.par or 'kosong'}") for s in aktif if not s.par or s.par not in parents],
            "Hubungkan orang tua di profil murid (tab Orang tua).", "STUDENT_MASTER.Parent ID → PARENT_MASTER")
        add("murid_tanpa_kelas", "Data murid", "Murid aktif tanpa kode kelas", "kritis", len(aktif),
            [_murid(s) for s in aktif if not kode_dipakai(s)], "Isi kelas di profil murid (Ubah kelas).", "STUDENT_MASTER Kode Kelas (ubah / terbaca)")
        add("murid_tanpa_guru", "Data murid", "Murid aktif tanpa guru", "tinggi", len(aktif),
            [_murid(s) for s in aktif if not guru_dipakai(s)], "Isi guru di profil murid.", "STUDENT_MASTER Guru (ubah / asli)")
        add("murid_tanpa_program", "Data murid", "Murid aktif tanpa program / level", "sedang", len(aktif),
            [_murid(s) for s in aktif if not (s.prog_in or s.program or s.level_in or s.level)], "Isi program dan level di profil murid.",
            "STUDENT_MASTER Program / Level")
        add("murid_tanpa_status", "Data murid", "Murid tanpa status tercatat", "tinggi", len(semua),
            [_murid(s, "tanpa Status Awal dan tanpa perubahan status") for s in semua if not s.st_base and fold(s.std) not in punya_event],
            "Tetapkan status lewat Ubah status (aktif / cuti / OFF).", "STUDENT_MASTER Status Awal + STATUS_EVENT")
        add("murid_tanpa_harga", "Data keuangan", "Murid aktif tanpa harga SPP", "kritis", len(aktif),
            [_murid(s) for s in aktif if harga_dipakai(s) is None], "Isi harga SPP di Ubah murid - tanpa harga, nota tidak bisa dibuat.",
            "STUDENT_MASTER Harga SPP (ubah / asli)")
        nama = defaultdict(list)
        for s in semua:
            if s.nama:
                nama[re.sub(r"\s+", " ", fold(s.nama)).strip()].append(s)
        dup = [s for group in nama.values() if len(group) > 1 for s in group]
        add("murid_duplikat", "Data murid", "Kemungkinan murid ganda (nama sama)", "sedang", len(semua),
            [_murid(s, f"{s.std} · ID v1 {s.v1 or '-'}") for s in dup], "Periksa apakah dua baris ini orang yang sama; gabungkan bila ya.",
            "STUDENT_MASTER Nama Murid")

        # ---- Data orang tua
        dipakai = {s.par for s in semua if s.par}
        ortu = [p for pid, p in parents.items() if pid in dipakai]
        add("ortu_tanpa_kontak", "Data orang tua", "Orang tua tanpa kontak (WhatsApp / email)", "tinggi", len(ortu),
            [{"label": p.nama or p.pid, "detail": p.pid, "url": reverse("students:parent_detail", args=[p.pid])}
             for p in ortu if not (p.wa or "").strip() and not (p.email or "").strip()],
            "Lengkapi kontak di profil orang tua.", "PARENT_MASTER WhatsApp / Email")
        by_wa = defaultdict(list)
        for p in parents.values():
            d = _digits(p.wa)
            if len(d) >= 9:
                by_wa[d].append(p)
        dup_p = [p for group in by_wa.values() if len(group) > 1 for p in group]
        add("ortu_duplikat", "Data orang tua", "Kemungkinan orang tua ganda (nomor WhatsApp sama)", "sedang", len(parents),
            [{"label": p.nama or p.pid, "detail": f"{p.pid} · nomor sama dengan orang tua lain", "url": reverse("students:parent_detail", args=[p.pid])}
             for p in dup_p], "Gabungkan bila orang yang sama, atau perbaiki nomornya.", "PARENT_MASTER WhatsApp")

        # ---- Kelas & guru & jadwal
        def _kelas(k, detail=""):
            return {"label": k.row.code, "detail": detail or f"{k.row.tipe or '-'} · {k.aktif} murid aktif", "url": reverse("classes:detail", args=[k.row.code])}
        add("kelas_tanpa_guru", "Data kelas", "Kelas aktif tanpa guru", "tinggi", len(aktif_k),
            [_kelas(k) for k in aktif_k if not (k.row.guru or "").strip()], "Tetapkan guru di detail kelas.", "CLASS_MASTER Guru")
        add("kelas_tanpa_jadwal", "Data jadwal", "Kelas aktif tanpa jadwal resmi", "tinggi", len(aktif_k),
            [_kelas(k) for k in aktif_k if fold(k.row.code) not in jadwal], "Tambahkan slot jadwal di detail kelas agar sesi bisa dibuat.",
            "CLASS_SCHEDULE")
        add("guru_tidak_dikenal", "Data guru", "Murid aktif dengan guru yang tidak ada di daftar guru", "sedang", len(aktif),
            [_murid(s, f"Guru: {guru_dipakai(s)}") for s in aktif if guru_dipakai(s) and teacher_key(guru_dipakai(s)) not in guru_dikenal],
            "Samakan nama guru dengan daftar Guru (atau tambahkan gurunya).", "STUDENT_MASTER Guru → TEACHER_MASTER")
        guru_aktif = [t for t in data.teachers if same(t.status, "ACTIVE")]
        add("guru_tanpa_kontak", "Data guru", "Guru aktif tanpa telepon / email", "rendah", len(guru_aktif),
            [{"label": t.name, "detail": t.tid, "url": reverse("masterdata:teacher", args=[t.tid])} for t in guru_aktif
             if not (t.phone or "").strip() and not (t.email or "").strip()], "Lengkapi kontak di profil guru.", "TEACHER_MASTER Phone / Email")

        # ---- Sesi & kehadiran
        lalu = [s for s in data.sesi if as_date(s.tgl) and as_date(s.tgl) < data.today]
        def _sesi(s, detail):
            return {"label": f"{s.kode or s.kelas or s.sid} · {as_date(s.tgl):%d/%m/%Y}", "detail": detail, "url": reverse("classes:session", args=[s.sid])}
        add("sesi_belum_konfirmasi", "Data jadwal", "Sesi lampau belum dikonfirmasi", "tinggi", len(lalu),
            [_sesi(s, f"{s.guru or 'guru -'} · masih Terjadwal") for s in lalu if same(s.status, "SCHEDULED")],
            "Buka sesi, isi realisasi dan kehadiran, lalu simpan.", "SESI status SCHEDULED, tanggal < hari ini")
        done = [s for s in data.sesi if fold(s.status) in ("realized", "make-up")]
        ada = set(Kehadiran.objects.filter(branch=data.branch, sid__in=[s.sid for s in done]).values_list("sid", flat=True))
        add("sesi_tanpa_absen", "Data jadwal", "Sesi terlaksana tanpa catatan kehadiran", "sedang", len(done),
            [_sesi(s, "terlaksana, belum ada absensi") for s in done if s.sid not in ada], "Isi kehadiran murid di halaman sesi.", "SESI + KEHADIRAN")

        # ---- Keuangan
        spp = [k for k in kas_rows(data) if same(k.row.jenis, "SPP") and same(k.dihitung, "YA") and as_date(k.row.bulan) and as_date(k.row.bulan) >= KAS_START]
        add("kas_tak_tertaut", "Data keuangan", "Penerimaan SPP tanpa murid tertaut", "kritis", len(spp),
            [{"label": f"{as_date(k.row.bulan):%b %Y} · Rp {int(k.row.nominal or 0):,}".replace(",", "."), "detail": (k.row.ket or "")[:90], "url": ""}
             for k in spp if not k.s[0] and not same(k.row.kor1, BUKAN_MURID)],
            "Isi 'Murid (koreksi)' pada baris buku kas (atau BUKAN MURID).", "BUKU_KAS Student ID sistem / koreksi")
        add("kas_lemah", "Data keuangan", "Tautan pembayaran berkeyakinan lemah (belum dikoreksi)", "sedang", len(spp),
            [{"label": f"{as_date(k.row.bulan):%b %Y} · {k.row.murid_sys or '-'}", "detail": (k.row.ket or "")[:90], "url": ""}
             for k in spp if fold(k.row.yakin).startswith("lemah") and not k.row.kor1],
            "Pastikan murid yang ditautkan benar; isi koreksi bila salah.", "BUKU_KAS Keyakinan")
        def _beda(r):
            b, t = as_date(r.bulan), as_date(r.tgl)
            return b and t and ((t.year, t.month) != (b.year, b.month) and abs((t.year - b.year) * 12 + t.month - b.month) > 1 or t > data.today)
        kas_tgl = [r for r in data.kas if as_date(r.bulan) and as_date(r.tgl)]
        add("kas_tanggal", "Data keuangan", "Tanggal buku kas tidak cocok dengan bulannya (atau di masa depan)", "tinggi", len(kas_tgl),
            [{"label": f"{r.lid}", "detail": f"bulan {as_date(r.bulan):%b %Y} · tanggal {as_date(r.tgl):%d/%m/%Y} · {(r.ket or '')[:60]}", "url": ""}
             for r in kas_tgl if _beda(r)],
            "Perbaiki tanggal di buku kas sumber (kemungkinan salah ketik tahun), lalu unggah ulang.", "BUKU_KAS Bulan vs Tanggal")
        bukti = list(BuktiBayar.objects.for_branch(data.branch))
        add("bukti_belum_verifikasi", "Data keuangan", "Bukti bayar belum diverifikasi", "sedang", len(bukti),
            [{"label": b.bid, "detail": f"{b.std} · {b.per}", "url": ""} for b in bukti if same(b.ver, "Belum Diverifikasi")],
            "Finance memverifikasi bukti bayar.", "BUKTI_BAYAR Status Verifikasi")

        # ---- Riwayat status & isu
        add("aktif_tanpa_riwayat", "Riwayat status", "Murid aktif tanpa riwayat status", "sedang", len(aktif),
            [_murid(s) for s in aktif if fold(s.v1) not in punya_riwayat and fold(s.std) not in punya_event],
            "Catat perubahan status (MASUK) agar matriks lifecycle lengkap.", "D_BULAN + STATUS_EVENT")
        terbuka = [i for i in data.issues if not any(same(i.status, x) for x in ("RESOLVED", "CLOSED")) and not same(i.still, "CLEARED")]
        add("isu_kritis", "Isu data", "Isu data kritis terbuka", "kritis", len(data.issues),
            [{"label": i.iid, "detail": (i.desc or i.type or "")[:110], "url": reverse("students:detail", args=[i.std]) if i.std else ""}
             for i in terbuka if same(i.sev, "CRITICAL")], "Tinjau dan putuskan isu kritis.", "ISSUE_UNIT Severity CRITICAL")
        add("isu_error", "Isu data", "Isu data ERROR terbuka", "tinggi", len(data.issues),
            [{"label": i.iid, "detail": (i.desc or i.type or "")[:110], "url": reverse("students:detail", args=[i.std]) if i.std else ""}
             for i in terbuka if same(i.sev, "ERROR")], "Perbaiki data sesuai deskripsi isu.", "ISSUE_UNIT Severity ERROR")
        return out
    return data.memo("mgmt_data_health", build)


def skor(cek):
    dihitung = [c for c in cek if c.diperiksa]
    w = sum(BOBOT[c.tingkat] for c in dihitung)
    return round(sum(BOBOT[c.tingkat] * (1 - c.n / c.diperiksa) for c in dihitung) * 100 / w) if w else None
