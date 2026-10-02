import datetime

import pytest

from branches.models import BranchSetting
from dashboards.calc.base import BranchData, fixed
from dashboards.calc.kas import bagian, bulanan, dihitung, kas_terakhir, ringkasan_spp, spp_murid
from dashboards.calc.laporan import Filter
from dashboards.tests.helpers import make_rows
from finance.models import BukuKas
from students.models import DBulan, DMurid, StudentMaster

D = datetime.date
SEP, AGU, JUN24 = D(2026, 9, 1), D(2026, 8, 1), D(2024, 6, 1)


def kas(bulan, nominal, ss1="", sb1=None, ss2="", sb2=None, jenis="SPP", dihitung="YA", **extra):
    return {"bulan": bulan, "tgl": extra.pop("tgl", bulan), "jenis": jenis, "nominal": nominal, "dihitung": dihitung,
            "ss1": ss1, "sb1": sb1, "ss2": ss2, "sb2": sb2, "lid": extra.pop("lid", ""), **extra}


@pytest.fixture
def data(branch):
    BranchSetting.objects.create(branch=branch, key="jurnal_agu", value_text="Revisi Jurnal Penerimaan (dipakai Arus Kas)")
    make_rows(StudentMaster, branch, {"std": "STD-000001"}, {"std": "STD-000002"}, {"std": "STD-000003"}, {"std": "STD-000004"})
    make_rows(DMurid, branch, {"v1": "A", "nama": "Ani", "std": "STD-000001"}, {"v1": "B", "nama": "Budi", "std": "STD-000002"},
              {"v1": "C", "nama": "Budi", "std": "STD-000003"}, {"v1": "E", "nama": "Eko", "std": "STD-000004"})
    make_rows(DBulan, branch, *[{"key": f"{v}|202609", "v1": v, "bulan": SEP, "status": s}
                                for v, s in (("A", "Aktif"), ("B", "Aktif"), ("C", "Cuti"), ("E", "Aktif"))])
    make_rows(BukuKas, branch,
              kas(SEP, 600000, "STD-000001", 600000, tgl=D(2026, 9, 12), lid="BK-1"),
              kas(SEP, 500000, "std-000002", 250000, "STD-000003", 250000, yakin="Lemah - nama mirip", lid="BK-2"),
              kas(SEP, 300000, lid="BK-3"),                                                    # belum tertaut
              kas(SEP, 200000, "STD-000004", 200000, kor1="BUKAN MURID", lid="BK-4"),          # koreksi: bukan murid
              kas(SEP, 400000, "STD-000004", 400000, kor1="Budi [B]", kor2="Ani", lid="BK-5"),  # koreksi: dua murid
              kas(SEP, 999, "STD-000001", 999, jenis="Lainnya", lid="BK-6"),                   # bukan SPP
              kas(SEP, 777, "STD-000001", 777, dihitung="TIDAK", lid="BK-7"),                  # tidak dihitung
              kas(AGU, 100000, "STD-000001", 100000, versi="R · Revisi", dihitung="TIDAK", tgl=D(2026, 8, 30), lid="BK-8"),
              kas(AGU, 90000, "STD-000001", 90000, versi="T · Tersembunyi", dihitung="YA", lid="BK-9"),
              kas(D(2026, 1, 1), 50000, "STD-000001", 50000, lid="BK-10"))
    return BranchData(branch, D(2026, 9, 30))


def by_lid(data, lid):
    return next(r for r in data.kas if r.lid == lid)


@pytest.mark.django_db
def test_shares_follow_corrections(data):
    assert bagian(data, by_lid(data, "BK-1")) == (["STD-000001", "", "", ""], [600000, 0, 0, 0])
    assert bagian(data, by_lid(data, "BK-3")) == (["", "", "", ""], [0, 0, 0, 0])
    assert bagian(data, by_lid(data, "BK-4")) == (["", "", "", ""], [0, 0, 0, 0])
    assert bagian(data, by_lid(data, "BK-5")) == (["STD-000002", "STD-000001", "", ""], [200000, 200000, 0, 0])


@pytest.mark.django_db
def test_august_rows_follow_the_journal_choice(data, branch):
    assert [dihitung(data, by_lid(data, x)) for x in ("BK-8", "BK-9", "BK-1")] == ["YA", "TIDAK", "YA"]
    BranchSetting.objects.filter(branch=branch, key="jurnal_agu").update(value_text="jurnal penerimaan (tersembunyi)")
    fresh = BranchData(branch, D(2026, 9, 30))
    assert [dihitung(fresh, by_lid(fresh, x)) for x in ("BK-8", "BK-9")] == ["TIDAK", "YA"]


@pytest.mark.django_db
def test_monthly_totals_and_student_spp(data):
    rows = {b: [t, l, n] for b, t, l, n in bulanan(data)}
    assert rows[SEP] == [2000000, 1500000, 500000]
    assert rows[AGU] == [100000, 100000, 0]
    assert spp_murid(data, SEP) == {"std-000001": 800000, "std-000002": 450000, "std-000003": 250000}
    assert spp_murid(data, JUN24) == {}


@pytest.mark.django_db
def test_spp_kpis_for_the_report_month(data):
    r = ringkasan_spp(data, Filter(SEP))
    assert r["spp"] == [2000000, 2150000, 3, "2  ·  67%", 1, 1, 1]
    assert [b.v1 for b in r["belum_bayar"]] == ["E"]
    assert sorted(r["per_baris"].values()) == [(0, "Belum ada pembayaran"), (250000, "Sudah ada pembayaran"),
                                               (450000, "Sudah ada pembayaran"), (800000, "Sudah ada pembayaran")]


@pytest.mark.django_db
def test_months_before_the_cash_book_and_undecided_august(data, branch):
    early = ringkasan_spp(data, Filter(JUN24))
    assert early["spp"][:2] == ["—", "—"] and early["spp"][3:6] == ["—", "—", "—"]
    assert set(early["per_baris"].values()) == {(0, "(belum ada buku kas)")}
    BranchSetting.objects.filter(branch=branch, key="jurnal_agu").update(value_text="BELUM DIPUTUSKAN")
    agu = ringkasan_spp(BranchData(branch, D(2026, 9, 30)), Filter(AGU))
    assert agu["keputusan"] and agu["spp"][3:6] == ["perlu keputusan", "perlu keputusan", "—"]
    assert agu["belum_bayar"] == []


@pytest.mark.django_db
def test_last_cash_book_month(data):
    k = kas_terakhir(data)
    assert (k["bulan"], k["total"], k["tgl"], k["prev_bulan"], k["prev_total"]) == (SEP, 2000000, D(2026, 9, 12), AGU, 100000)
    assert fixed(66919995) == "66.919.995" and fixed(0) == "0" and fixed(1234.5) == "1.235"


@pytest.mark.django_db
def test_empty_branch_has_no_cash_book(other_branch):
    data = BranchData(other_branch, D(2026, 9, 30))
    assert kas_terakhir(data) is None and bulanan(data) == []
    assert ringkasan_spp(data, Filter(SEP))["spp"] == [0, 0, 0, 0, 0, 0, 0]


@pytest.mark.django_db
def test_august_rows_have_no_student_while_the_journal_is_undecided(data, branch):
    assert bagian(data, by_lid(data, "BK-8")) == (["STD-000001", "", "", ""], [100000, 0, 0, 0])
    BranchSetting.objects.filter(branch=branch, key="jurnal_agu").update(value_text="BELUM DIPUTUSKAN")
    fresh = BranchData(branch, D(2026, 9, 30))
    assert bagian(fresh, by_lid(fresh, "BK-8")) == (["", "", "", ""], [0, 0, 0, 0])
    assert bagian(fresh, by_lid(fresh, "BK-1")) == (["STD-000001", "", "", ""], [600000, 0, 0, 0])
