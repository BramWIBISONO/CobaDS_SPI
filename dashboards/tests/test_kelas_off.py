import datetime

import pytest

from branches.models import BranchSetting
from classes.models import ClassMaster, ClassMembers
from dashboards.calc.base import BranchData
from dashboards.calc.kelas import daftar_kelas, ringkasan_kelas
from dashboards.calc.off import KEMBALI, daftar_off, ringkasan_off
from dashboards.tests.helpers import make_rows
from students.models import FollowUp, StatusEvent, StudentMaster, StudentOff

D = datetime.date


@pytest.fixture
def setting(branch):
    def put(key, value):
        BranchSetting.objects.create(branch=branch, key=key, **BranchSetting.split_value(value))
    return put


@pytest.mark.django_db
def test_class_capacity_and_status(branch, setting):
    for k, v in (("F", 1), ("P", 4), ("G", 10), ("S", 20)):
        setting(k, v)
    make_rows(ClassMaster, branch, *[{"class_id": f"CLS-{i}", "code": code, "tipe": tipe} for i, (code, tipe) in enumerate(
        (("P001", "Partner"), ("f002", "Focus"), ("G003", "Group"), ("P004", "Partner"), ("X005", "Partner"), ("P006", "Partner")))])
    make_rows(StudentMaster, branch,
              *[{"std": f"STD-0000{i:02d}", "kode_read": "P001", "st_base": "ACTIVE"} for i in range(1, 4)],
              {"std": "STD-000010", "kode_read": "F002", "st_base": "ACTIVE"},
              {"std": "STD-000011", "kode_read": "x", "kode_in": "F002", "st_base": "ACTIVE"},
              {"std": "STD-000012", "kode_read": "G003", "st_base": "ON LEAVE"},
              {"std": "STD-000013", "kode_read": "X005", "st_base": "ACTIVE"})
    make_rows(ClassMembers, branch, {"code": "P004", "std": "STD-000099"})
    data = BranchData(branch, D(2026, 9, 30))
    got = {k.row.code: [k.kapasitas, k.aktif, k.cuti, k.status_kapasitas, k.status_kelas, k.kursi_kosong] for k in daftar_kelas(data)}
    assert got == {"P001": [4, 3, 0, "NORMAL", "ACTIVE", 1], "f002": [1, 2, 0, "OVER CAPACITY", "ACTIVE", 0],
                   "G003": [10, 0, 1, "KOSONG", "CUTI", 0], "P004": [4, 0, 0, "KOSONG", "INACTIVE", 0],
                   "X005": ["", 1, 0, "NORMAL", "ACTIVE", 0], "P006": [4, 0, 0, "KOSONG", "UNKNOWN", 0]}
    assert ringkasan_kelas(data) == {"aktif": 3, "kursi": 1, "penuh": 0, "melebihi": 1}


@pytest.mark.django_db
def test_off_status_follow_up_and_priority(branch, setting):
    setting("off_lama", 3)
    make_rows(StudentOff, branch,
              {"off_id": "OFF-1", "std": "STD-000001", "month": D(2026, 9, 1), "status_src": ""},          # baru off, belum follow-up
              {"off_id": "OFF-2", "std": "STD-000002", "month": D(2026, 6, 1), "status_src": "MASIH OFF"},  # 3 bln, belum follow-up
              {"off_id": "OFF-3", "std": "STD-000003", "month": D(2025, 1, 1), "status_src": ""},          # lama, ada tindak lanjut
              {"off_id": "OFF-4", "std": "STD-000004", "month": D(2026, 3, 1), "tgl": D(2026, 3, 20), "status_src": ""},  # aktif lagi
              {"off_id": "OFF-5", "std": "STD-000005", "month": D(2026, 2, 1), "status_src": "STATUS KOSONG (cek)"},
              {"off_id": "OFF-6", "std": "STD-000006", "month": D(2025, 5, 1), "status_src": ""},          # follow-up jatuh tempo
              {"off_id": "", "std": "STD-000007", "month": D(2026, 9, 1)})                                 # tanpa Off Record ID
    make_rows(StatusEvent, branch, {"eid": "EVT-1", "std": "STD-000004", "tgl": D(2026, 3, 19), "status": "ACTIVE"},
              {"eid": "EVT-2", "std": "STD-000004", "tgl": D(2026, 4, 2), "status": "ACTIVE"})
    make_rows(FollowUp, branch,
              {"fid": "FU-1", "std": "STD-000003", "tgl": D(2024, 12, 1), "aksi": "Kasus ditutup"},             # sebelum bulan Off: diabaikan
              {"fid": "FU-2", "std": "STD-000003", "tgl": D(2025, 2, 3), "aksi": "Hubungi orang tua"},
              {"fid": "FU-3", "std": "std-000003", "tgl": D(2025, 3, 4), "aksi": "", "next": D(2026, 10, 9)},
              {"fid": "FU-4", "std": "STD-000006", "tgl": D(2025, 6, 1), "aksi": "Telepon", "next": D(2026, 9, 30)})
    data = BranchData(branch, D(2026, 9, 30))
    got = {o.row.off_id: [o.status, o.lama, o.aksi, o.fu_tgl, o.fu_next, o.prioritas] for o in daftar_off(data)}
    assert got == {
        "OFF-1": ["MASIH OFF", 0, "", None, None, "MENDESAK"],
        "OFF-2": ["MASIH OFF", 3, "", None, None, "MINGGU INI"],
        "OFF-3": ["MASIH OFF", 20, "Hubungi orang tua", D(2025, 3, 4), D(2026, 10, 9), "PANTAU"],
        "OFF-4": [KEMBALI, "", "", None, None, "SELESAI"],
        "OFF-5": ["STATUS KOSONG (cek)", "", "", None, None, "PANTAU"],
        "OFF-6": ["MASIH OFF", 16, "Telepon", D(2025, 6, 1), D(2026, 9, 30), "HARI INI"],
    }
    assert ringkasan_off(data) == {"masih": 4, "perlu": 3, "baru": 1}
