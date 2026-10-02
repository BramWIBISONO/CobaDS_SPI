import datetime

import pytest

from dashboards.calc.base import BranchData, label
from dashboards.calc.status import kelompok, kode_dipakai, semua_status_sekarang, status_akhir_periode, status_sekarang
from dashboards.tests.helpers import make_rows
from students.models import DBulan, DMurid, StatusEvent, StudentMaster

D = datetime.date


def test_group_follows_the_d_bulan_rule():
    assert [kelompok(s) for s in ("Aktif", "baru", "Rejoin", "Cuti", "OFF", "", None, "Lulus")] == \
        ["Aktif", "Aktif", "Aktif", "Cuti", "Off", "", "", ""]


@pytest.mark.django_db
def test_current_status_uses_the_latest_event_up_to_today(branch):
    a, b, c = make_rows(StudentMaster, branch, {"std": "STD-000001", "st_base": "ACTIVE"}, {"std": "STD-000002", "st_base": ""},
                        {"std": "STD-000003", "st_base": "OFF"})
    make_rows(StatusEvent, branch,
              {"eid": "EVT-000001", "std": "std-000001", "tgl": D(2026, 10, 3), "status": "ON LEAVE"},
              {"eid": "EVT-000002", "std": "STD-000001", "tgl": D(2026, 10, 3), "status": "OFF"},      # tanggal sama: baris kemudian menang
              {"eid": "EVT-000003", "std": "STD-000003", "tgl": D(2026, 12, 1), "status": "ACTIVE"})   # sesudah hari ini: diabaikan
    data = BranchData(branch, D(2026, 10, 5))
    assert [status_sekarang(data, s) for s in (a, b, c)] == ["OFF", "PENDING", "OFF"]
    assert semua_status_sekarang(data) == {"std-000001": "OFF", "std-000002": "PENDING", "std-000003": "OFF"}


@pytest.mark.django_db
def test_status_at_period_end_uses_events_then_history_then_baseline(branch):
    s1, s2 = make_rows(StudentMaster, branch, {"std": "STD-000001", "v1": "M001", "st_base": "ON LEAVE"},
                       {"std": "STD-000002", "v1": "M002", "st_base": "PENDING"})
    make_rows(DBulan, branch, {"key": "M001|202608", "v1": "M001", "bulan": D(2026, 8, 1), "status": "Baru"},
              {"key": "M002|202608", "v1": "M002", "bulan": D(2026, 8, 1), "status": "Lulus"})
    make_rows(StatusEvent, branch, {"eid": "EVT-000001", "std": "STD-000002", "tgl": D(2026, 10, 31), "status": "ACTIVE"})
    data = BranchData(branch, D(2026, 11, 2))
    assert [status_akhir_periode(data, s, D(2026, 8, 1)) for s in (s1, s2)] == ["ACTIVE", ""]
    assert [status_akhir_periode(data, s, D(2026, 10, 1)) for s in (s1, s2)] == ["ON LEAVE", "ACTIVE"]


def test_class_code_in_use_prefers_the_edit():
    assert kode_dipakai(StudentMaster(kode_in="P01", kode_read="F02")) == "P01"
    assert kode_dipakai(StudentMaster(kode_in="", kode_read="F02")) == "F02"


@pytest.mark.django_db
def test_lists_follow_the_excel_build(branch):
    make_rows(DMurid, branch, {"v1": "M1", "tipe_kelas_rapi": "Partner", "mode_rapi": "Onsite"},
              {"v1": "M2", "tipe_kelas_rapi": "Focus", "mode_rapi": "Online"}, {"v1": "M3", "tipe_kelas_rapi": "", "mode_rapi": ""})
    make_rows(DBulan, branch,
              {"key": "M1|202401", "grade": "Development 2.1", "guru": "Mr. Bram", "guru_asli": "bram"},
              {"key": "M2|202401", "grade": "Foundation 1.0", "guru": "Ms. Linda", "guru_asli": "linda"},
              {"key": "M3|202401", "grade": "Foundation 1.2", "guru": "Ms. Linda", "guru_asli": "Linda"},
              {"key": "M1|202402", "grade": "Development 2.1", "guru": "Mr. Bram", "guru_asli": "Bram"},
              {"key": "M2|202402", "grade": "Robotik", "guru": "Mr. Aldi", "guru_asli": ""})
    data = BranchData(branch, D(2026, 9, 30))
    assert data.programs == ["Foundation", "Development", "Robotik"]
    assert data.levels == ["Foundation 1.0", "Foundation 1.2", "Development 2.1", "Robotik"]
    assert (data.tipes, data.modes) == (["Focus", "Partner"], ["Online", "Onsite"])
    assert data.gurus == ["Mr. Bram", "Ms. Linda"]                     # seri 2-2: kemunculan pertama dulu; tanpa guru asli tidak dihitung
    assert [label(m) for m in data.months_hist][:2] == ["Jan 2024", "Feb 2024"] and len(data.months_hist) == 33
