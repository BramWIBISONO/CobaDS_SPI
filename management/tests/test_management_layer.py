"""Finance Control, Nota SPP, Data Health, skor kesehatan, izin & isolasi cabang, ekspor."""
import datetime

import pytest
from django.test import Client
from django.urls import reverse

from audit.models import AuditLog
from branches.models import BranchSetting
from dashboards.calc.base import BranchData
from dashboards.tests.helpers import make_rows
from finance.models import BukuKas, NotaLog, SppTagihan
from management.services import data_health, finance, health
from students.models import DBulan, ParentMaster, StudentMaster

D = datetime.date
TODAY = D(2026, 10, 6)


def _setting(branch, key, value):
    BranchSetting.objects.update_or_create(branch=branch, key=key, defaults=BranchSetting.split_value(value))


@pytest.fixture
def jkt(branch, other_branch):
    _setting(branch, "nota_awalan", "SPI-JKT/SPP/")
    _setting(branch, "nota_kop", "SPI Jakarta")
    _setting(branch, "mulai_v4", D(2026, 10, 1))
    make_rows(ParentMaster, branch, {"pid": "PAR-00001", "nama": "Ibu Sari", "wa": "0812000001"})
    make_rows(StudentMaster, branch,
              {"std": "STD-000001", "v1": "M1", "nama": "Ani Lunas", "harga": 500000, "par": "PAR-00001", "kode_in": "P001", "guru_in": "Mr. Bram", "st_base": "ACTIVE"},
              {"std": "STD-000002", "v1": "M2", "nama": "Budi Sebagian", "harga": 600000, "kode_in": "P001", "guru_in": "Mr. Bram", "st_base": "ACTIVE"},
              {"std": "STD-000003", "v1": "M3", "nama": "Citra Belum", "harga": 450000, "kode_in": "P001", "guru_in": "Mr. Bram", "st_base": "ACTIVE"},
              {"std": "STD-000004", "v1": "M4", "nama": "Dodi Tanpa Harga", "kode_in": "P001", "guru_in": "Mr. Bram", "st_base": "ACTIVE"})
    make_rows(DBulan, branch, *[{"key": f"M{i}|202609", "v1": f"M{i}", "bulan": D(2026, 9, 1), "status": "Aktif"} for i in range(1, 5)])
    make_rows(BukuKas, branch,
              {"lid": "KAS-1", "bulan": D(2026, 9, 1), "tgl": D(2026, 9, 3), "jenis": "SPP", "dihitung": "YA", "nominal": 500000,
               "per_sys": "2026-09", "ss1": "STD-000001", "sb1": 500000, "ket": "SPP Ani September"},
              {"lid": "KAS-2", "bulan": D(2026, 9, 1), "tgl": D(2026, 9, 4), "jenis": "SPP", "dihitung": "YA", "nominal": 200000,
               "per_sys": "2026-08", "per_in": "2026-09", "ss1": "STD-000002", "sb1": 200000, "ket": "SPP Budi (koreksi periode)"},
              {"lid": "KAS-3", "bulan": D(2026, 9, 1), "tgl": D(2026, 9, 5), "jenis": "SPP", "dihitung": "YA", "nominal": 300000,
               "per_sys": "2026-09", "ket": "transfer tanpa nama"},
              {"lid": "KAS-4", "bulan": D(2025, 12, 1), "tgl": D(2026, 12, 7), "jenis": "SPP", "dihitung": "YA", "nominal": 100000,
               "per_sys": "2025-12", "ss1": "STD-000001", "sb1": 100000, "ket": "tahun salah ketik"})
    make_rows(StudentMaster, other_branch, {"std": "STD-000001", "v1": "X1", "nama": "Murid Cabang Lain", "harga": 999000})
    return branch


def _data(branch):
    return BranchData(branch, TODAY)


@pytest.mark.django_db
def test_nota_status_follows_excel_rules(jkt):
    data = _data(jkt)
    by = {s.std: s for s in data.students}
    sep = D(2026, 9, 1)
    ani, budi, citra, dodi = (finance.status_bayar(data, by[k], sep) for k in ("STD-000001", "STD-000002", "STD-000003", "STD-000004"))
    assert (ani.status, ani.tagihan, ani.bayar, ani.sisa) == ("LUNAS", 500000, 500000, 0)
    assert (budi.status, budi.bayar, budi.sisa) == ("SEBAGIAN", 200000, 400000)        # periode koreksi (per_in) dipakai
    assert (citra.status, citra.bayar) == ("BELUM TERCATAT", 0)
    assert dodi.status == "HARGA BELUM TERCATAT" and not dodi.bisa_nota
    assert finance.status_bayar(data, by["STD-000001"], D(2026, 10, 1)).status == "TIDAK ADA TAGIHAN"   # >= mulai_v4, tanpa SPP_TAGIHAN
    _setting(jkt, "jurnal_agu", "BELUM DIPUTUSKAN")
    assert finance.status_bayar(_data(jkt), by["STD-000001"], D(2026, 8, 1)).status == "PERLU KEPUTUSAN"


@pytest.mark.django_db
def test_official_bill_path_from_spp_tagihan(jkt):
    make_rows(SppTagihan, jkt, {"tid": "TG-1", "per": "2026-10", "std": "STD-000003", "harga": 450000, "diskon": 50000, "adj": 0})
    data = _data(jkt)
    citra = next(s for s in data.students if s.std == "STD-000003")
    st = finance.status_bayar(data, citra, D(2026, 10, 1))
    assert st.sumber == "SPP_TAGIHAN" and st.tagihan == 400000
    assert st.status in ("BELUM JATUH TEMPO", "BELUM DIBAYAR", "TERLAMBAT", "PERLU KLARIFIKASI")


@pytest.mark.django_db
def test_finance_control_totals_are_traceable(jkt):
    k = finance.kendali(_data(jkt), D(2026, 9, 1))
    assert k["aktif"] == 4 and k["potensi"] == 1550000                # harga 3 murid aktif ber-harga
    assert k["diterima_aktif"] == 700000 and k["outstanding"] == 850000
    assert k["collection"] == round(700000 * 100 / 1550000, 1)
    assert k["tak_tertaut"]["n"] == 1 and k["tak_tertaut"]["rp"] == 300000
    assert k["hitung"]["LUNAS"] == 1 and k["hitung"]["HARGA BELUM TERCATAT"] == 1


@pytest.mark.django_db
def test_issue_nota_numbers_log_and_audit(jkt, make_user):
    fin = make_user("fin@spi.test", role="FINANCE", branch=jkt)
    c = Client()
    c.force_login(fin)
    page = c.get(reverse("management:nota_preview", args=["STD-000001", "2026-09"]))
    assert page.status_code == 200 and "NOTA SPP" in page.content.decode() and "SPI-JKT/SPP/2026/0001" in page.content.decode()
    r = c.post(reverse("management:nota_issue", args=["STD-000001", "2026-09"]))
    log = NotaLog.objects.get(branch=jkt)
    assert r.status_code == 302 and log.no == "SPI-JKT/SPP/2026/0001" and log.status == "LUNAS" and log.tagihan == 500000
    assert log.kepada == "Ibu Sari"
    c.post(reverse("management:nota_issue", args=["STD-000002", "2026-09"]))
    assert NotaLog.objects.filter(branch=jkt).order_by("row_no").last().no == "SPI-JKT/SPP/2026/0002"
    assert AuditLog.objects.filter(branch=jkt, entity="NOTA_LOG").count() == 2
    blocked = c.post(reverse("management:nota_issue", args=["STD-000004", "2026-09"]))        # tanpa harga: tidak boleh
    assert blocked.status_code == 302 and NotaLog.objects.filter(branch=jkt).count() == 2
    assert c.get(reverse("management:nota_view", args=[log.pk])).status_code == 200


@pytest.mark.django_db
def test_nota_issue_requires_finance_verify_and_branch(jkt, other_branch, make_user):
    manager = make_user("mgr@spi.test", role="MANAGER", branch=jkt)
    c = Client()
    c.force_login(manager)
    assert c.get(reverse("management:nota_preview", args=["STD-000001", "2026-09"])).status_code == 200   # boleh lihat
    assert c.post(reverse("management:nota_issue", args=["STD-000001", "2026-09"])).status_code == 403
    other = make_user("fin2@spi.test", role="FINANCE", branch=other_branch)
    c.force_login(other)
    resp = c.get(reverse("management:nota_preview", args=["STD-000002", "2026-09"]))
    assert resp.status_code == 404                                   # murid cabang lain tidak terlihat


@pytest.mark.django_db
@pytest.mark.parametrize("role, center, finance_page", [
    ("MANAGER", 200, 200), ("BRANCH_ADMIN", 200, 200), ("FINANCE", 403, 200), ("CSO", 403, 403), ("ACADEMIC", 403, 403), ("TEACHER", 403, 403)])
def test_management_pages_follow_roles(jkt, make_user, role, center, finance_page):
    c = Client()
    c.force_login(make_user(f"{role.lower()}@spi.test", role=role, branch=jkt))
    assert c.get(reverse("management:center")).status_code == center
    assert c.get(reverse("management:data")).status_code == center
    assert c.get(reverse("management:finance")).status_code == finance_page
    assert c.get(reverse("management:nota")).status_code == finance_page


@pytest.mark.django_db
def test_every_management_page_renders_with_branch_data_only(jkt, make_user):
    c = Client()
    c.force_login(make_user("ba@spi.test", role="BRANCH_ADMIN", branch=jkt))
    for name in ("center", "health", "lifecycle", "finance", "nota", "operations", "data", "reports", "report_monthly"):
        resp = c.get(reverse(f"management:{name}"))
        assert resp.status_code == 200, name
        assert "Murid Cabang Lain" not in resp.content.decode(), name
    assert "Ani Lunas" in c.get(reverse("management:nota"), {"q": "ani", "periode": "2026-09"}).content.decode()


@pytest.mark.django_db
def test_data_health_finds_real_problems_with_links(jkt):
    cek = {c.key: c for c in data_health.cek_semua(_data(jkt))}
    assert cek["murid_tanpa_harga"].n == 1 and cek["murid_tanpa_harga"].terkena[0]["url"].endswith("/STD-000004/")
    assert cek["murid_tanpa_ortu"].n == 3
    assert cek["kas_tak_tertaut"].n == 1
    assert cek["kas_tanggal"].n == 1 and "07/12/2026" in cek["kas_tanggal"].terkena[0]["detail"]
    s = data_health.skor(list(cek.values()))
    assert s is not None and 0 <= s <= 100


@pytest.mark.django_db
def test_health_scores_are_explainable_and_skip_missing_data(jkt):
    data = _data(jkt)
    r = health.ringkasan(data, D(2026, 9, 1))
    fin = next(d for d in r["dimensi"] if d["key"] == "financial")
    coll = next(k for k in fin["komponen"] if k["key"] == "collection")
    assert coll["nilai"] == round(700000 * 100 / 1550000, 1) and coll["skor"] == health.peta("collection", coll["nilai"])
    op = next(d for d in r["dimensi"] if d["key"] == "operational")
    assert all(k["skor"] is None for k in op["komponen"] if k["nilai"] is None)       # tanpa sesi: tidak dihitung, bukan 0
    assert health.status_skor(85)[0] == "Sehat" and health.status_skor(40)[0] == "Kritis" and health.status_skor(None)[0] == "Tidak cukup data"
    items = health.keputusan(data, r, {"management.view", "management.finance"})
    kinds = {x["kat"] for x in items}
    assert "Data Issue" in kinds and all(x["modul"] and x["aksi"] for x in items)


@pytest.mark.django_db
def test_decision_insights_include_period_matched_affected_records_and_respect_finance_permission(jkt, make_user):
    for i in range(1, 5):
        make_rows(
            DBulan,
            jkt,
            {"key": f"M{i}|202608", "v1": f"M{i}", "bulan": D(2026, 8, 1), "status": "Aktif"},
        )
    DBulan.objects.filter(branch=jkt, key__in=["M1|202609", "M2|202609", "M3|202609"]).update(status="Off")
    DBulan.objects.filter(branch=jkt, key="M4|202609").update(status="")

    data = _data(jkt)
    summary = health.ringkasan(data, D(2026, 9, 1))
    items = health.keputusan(data, summary, {"management.view", "management.finance"})
    off = next(item for item in items if item["metrik"] == "Off baru")
    missing = next(item for item in items if item["metrik"] == "Hilang dari catatan")

    assert off["kat"] == "Kritis"
    assert off["ambang"] == "≥ 3 dan naik dari bulan lalu"
    assert off["sebelum"] == 0 and off["nilai"] == 3
    assert {record["detail"].split(" · ")[0] for record in off["records"]} == {
        "STD-000001", "STD-000002", "STD-000003"
    }
    assert all(record["url"].endswith(f"/{record['detail'].split(' · ')[0]}/") for record in off["records"])
    assert missing["records_total"] == 1
    assert missing["records"][0]["detail"].startswith("STD-000004 ·")

    restricted = health.keputusan(data, summary, {"management.view"})
    unmatched = next(item for item in restricted if item["metrik"] == "Baris kas tak tertaut")
    assert unmatched["records_restricted"] is True
    assert unmatched["records"] == []

    client = Client()
    client.force_login(make_user("decision-center@spi.test", role="BRANCH_ADMIN", branch=jkt))
    response = client.get(reverse("management:center"), {"periode": "2026-09"})
    html = response.content.decode()
    assert response.status_code == 200
    assert "Record terdampak" in html
    assert "Ani Lunas" in html and "Budi Sebagian" in html and "Citra Belum" in html
    assert reverse("students:detail", args=["STD-000001"]) in html


@pytest.mark.django_db
def test_exports_are_logged_and_scoped(jkt, make_user):
    c = Client()
    c.force_login(make_user("ba2@spi.test", role="BRANCH_ADMIN", branch=jkt))
    csv_body = c.get(reverse("management:lifecycle_export"), {"format": "csv"}).content.decode("utf-8-sig")
    assert "Ani Lunas" in csv_body and "Murid Cabang Lain" not in csv_body
    xlsx = c.get(reverse("management:finance"), {"periode": "2026-09", "ekspor": "xlsx"})
    assert xlsx["Content-Type"].startswith("application/vnd.openxmlformats")
    assert c.get(reverse("management:data"), {"ekspor": "csv"}).status_code == 200
    assert AuditLog.objects.filter(branch=jkt, action="EXPORT").count() == 3
