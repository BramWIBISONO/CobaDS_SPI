import datetime

import pytest

from dashboards.calc.base import BranchData
from dashboards.calc.laporan import Filter, baris_laporan, ringkasan_murid
from dashboards.tests.helpers import make_rows
from students.models import DBulan, DMurid

D = datetime.date
SEP, AGU = D(2026, 9, 1), D(2026, 8, 1)


def bulan(v1, b, status, grade="Development 2.1", guru="Mr. Bram", tipe="Partner", mode="Onsite"):
    return {"key": f"{v1}|{b:%Y%m}", "v1": v1, "bulan": b, "status": status, "grade": grade, "guru": guru, "guru_asli": guru,
            "tipe": tipe, "mode": mode}


@pytest.fixture
def data(branch):
    make_rows(DMurid, branch, *[{"v1": v, "nama": f"Murid {v}", "std": f"STD-00000{i}", "kode_kelas": f"P0{i}",
                                 "tipe_kelas_rapi": "Partner", "mode_rapi": "Onsite"} for i, v in enumerate("ABCDEF", 1)])
    make_rows(DBulan, branch,
              bulan("A", AGU, "Aktif"), bulan("A", SEP, "Off"),                                   # Off baru
              bulan("B", AGU, "Off"), bulan("B", SEP, "off"),                                     # Off lama
              bulan("C", SEP, "Baru", grade="Foundation 1.0", guru="Ms. Linda"),
              bulan("D", AGU, "Cuti"), bulan("D", SEP, "Rejoin", tipe="Focus", mode="Online"),
              bulan("E", SEP, "Cuti"),
              bulan("Z", SEP, "Aktif"))                                                          # tanpa D_MURID: hanya tren
    return BranchData(branch, D(2026, 9, 30))


@pytest.mark.django_db
def test_monthly_counts_follow_c_dash(data):
    r = ringkasan_murid(data, Filter(SEP))
    assert r["murid"] == [3, 2, 1, 1, 1, 2, 1]                          # total, aktif, baru, rejoin, cuti, off, off baru
    assert r["status"] == [["Aktif", 0], ["Baru", 1], ["Rejoin", 1], ["Cuti", 1], ["Off", 2]]   # status persis; 'off' = Off (tanpa beda huruf)
    assert [b.v1 for b in r["baru"]] == ["C"] and [b.v1 for b in r["off_baru"]] == ["A"]
    assert [b.v1 for b in r["daftar"]] == ["A", "B", "C", "D", "E"]     # F tidak punya baris bulan ini


@pytest.mark.django_db
def test_filters_use_the_month_row_and_ignore_case(data):
    r = ringkasan_murid(data, Filter(SEP, program="development", tipe="Partner"))
    assert [b.v1 for b in r["daftar"]] == ["A", "B", "E"]
    assert r["murid"][:2] == [1, 0]
    assert ringkasan_murid(data, Filter(SEP, guru="Ms. Linda"))["murid"] == [1, 1, 1, 0, 0, 0, 0]


@pytest.mark.django_db
def test_composition_and_trend(data):
    r = ringkasan_murid(data, Filter(SEP))
    assert r["level"] == [["Foundation 1.0", 1], ["Development 2.1", 1]]
    assert r["tipe"] == [["Partner", 1]]                                 # daftar tipe dari D_MURID; nilai dari baris bulan
    assert r["guru"][:2] == [["Mr. Bram", 1], ["Ms. Linda", 1]] and r["guru"][-1] == ["Lainnya / kosong", 0]
    tren = {t[0]: t[1:] for t in r["tren"]}
    assert len(r["tren"]) == 33 and tren["Sep 26"] == [3, 1, 2, 1] and tren["Agu 26"] == [1, 1, 1, 0]


@pytest.mark.django_db
def test_first_month_has_no_previous_month(data):
    rows = baris_laporan(data, Filter(D(2024, 1, 1)))
    assert all(not b.ikut and not b.off_baru for b in rows)
