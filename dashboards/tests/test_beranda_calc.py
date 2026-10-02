import datetime

import pytest

from audit.models import ImportLog
from branches.models import BranchSetting
from dashboards.calc.base import BranchData
from dashboards.calc.beranda import beranda, cari_murid
from dashboards.calc.operasional import bukti, kritis, periode_v4, teks_kritis
from dashboards.tests.helpers import make_rows
from finance.models import BuktiBayar, Periode
from quality.models import IssueUnit
from students.models import FollowUp, StatusEvent, StudentMaster

D = datetime.date


@pytest.mark.django_db
def test_critical_issues_and_payment_proofs(branch):
    make_rows(IssueUnit, branch, {"iid": "I1", "sev": "CRITICAL", "status": "OPEN"}, {"iid": "I2", "sev": "critical", "status": ""},
              {"iid": "I3", "sev": "CRITICAL", "status": "RESOLVED"}, {"iid": "I4", "sev": "CRITICAL", "status": "OPEN", "still": "CLEARED"},
              {"iid": "I5", "sev": "ERROR", "status": "OPEN"})
    make_rows(BuktiBayar, branch, {"bid": "B1", "ver": "Belum Diverifikasi"}, {"bid": "B2", "ver": "Tidak Cocok"},
              {"bid": "B3", "ver": "Perlu Klarifikasi"}, {"bid": "B4", "ver": "Verified"})
    data = BranchData(branch, D(2026, 9, 30))
    assert kritis(data) == 2 and bukti(data) == (1, 2)
    assert teks_kritis(data, 2) == "lihat TINDAKAN bagian 0" and teks_kritis(data, 0) == "tidak ada masalah kritis terbuka"
    BranchSetting.objects.create(branch=branch, key="jurnal_agu", value_text="BELUM DIPUTUSKAN")
    assert teks_kritis(BranchData(branch, D(2026, 9, 30)), 0) == "Jurnal Agustus 2026 perlu keputusan (SETTINGS)"


@pytest.mark.django_db
def test_operational_period_counts(branch):
    make_rows(StudentMaster, branch, {"std": "STD-000001", "st_base": "ACTIVE"}, {"std": "STD-000002", "st_base": "PENDING"})
    make_rows(StatusEvent, branch,
              {"eid": "E1", "std": "STD-000001", "tgl": D(2026, 10, 3), "status": "OFF", "jenis": "PERUBAHAN"},
              {"eid": "E2", "std": "STD-000009", "tgl": D(2026, 10, 9), "status": "ACTIVE", "jenis": "MASUK"},
              {"eid": "E3", "std": "STD-000008", "tgl": D(2026, 10, 9), "status": "ACTIVE", "jenis": "Aktif kembali (dari cuti)"})
    make_rows(FollowUp, branch, {"fid": "F1", "tgl": D(2026, 10, 1)}, {"fid": "F2", "tgl": D(2026, 9, 1)})
    data = BranchData(branch, D(2026, 10, 15))
    okt = periode_v4(data, D(2026, 10, 1))
    assert okt["status"] == [0, 0, 1, 1] and okt["baris"] == {"STD-000001": "OFF", "STD-000002": "PENDING"}
    assert okt["aktivitas"] == [1, 1, 0, 1, 0, 0, 0, 1, 0]


@pytest.mark.django_db
def test_home_summary_and_search(branch):
    make_rows(StudentMaster, branch, {"std": "STD-000001", "nama": "Ani Wijaya", "st_base": "ACTIVE", "kode_read": "P01", "guru": "Bram"},
              {"std": "STD-000002", "nama": "Budi", "st_base": "ON LEAVE"}, {"std": "STD-000003", "nama": "Wija", "st_base": ""})
    make_rows(Periode, branch, {"per": "2026-09", "label": "Sep 2026", "status": "OPEN"})
    make_rows(ImportLog, branch, {"batch": "IMP-JKT-20260930-01", "date": "2026-09-30 10:00", "file": "x.xlsm"})
    h = beranda(BranchData(branch, D(2026, 9, 30)))
    assert (h["aktif"], h["sub_aktif"]) == (1, "cuti 1  ·  pending 1  ·  status v4 (INPUT CENTER)")
    assert h["spp"] is None and h["sub_spp"] == "buku kas belum ada"
    assert h["judul"] == "Periode berjalan: Sep 2026   ·   riwayat DB Murid —   ·   buku kas —"
    assert (h["off"], h["sub_off"]) == (0, "0 perlu follow-up  ·  baru Off Sep 2026: 0")
    assert h["impor"].batch == "IMP-JKT-20260930-01"
    found = cari_murid(BranchData(branch, D(2026, 9, 30)), "wija")
    assert [(r["nama"], r["status"], r["kode"], r["guru"]) for r in found] == [("Ani Wijaya", "ACTIVE", "P01", "Bram"),
                                                                                ("Wija", "PENDING", "", "")]
    assert cari_murid(BranchData(branch, D(2026, 9, 30)), "  ") == []


@pytest.mark.django_db
def test_home_for_an_empty_branch(other_branch):
    h = beranda(BranchData(other_branch, D(2026, 9, 30)))
    assert (h["aktif"], h["off"], h["kelas"], h["kritis"], h["bukti"], h["spp"]) == (0, 0, 0, 0, 0, None)
    assert h["judul"].startswith("Periode berjalan: -") and h["impor"] is None
