import datetime

import pytest
from django.urls import reverse

from branches.models import BranchSetting
from dashboards.tests.helpers import make_rows
from finance.models import BukuKas
from students.models import DBulan, DMurid, StudentMaster

D = datetime.date
URL = "/laporan/"


@pytest.fixture
def data(branch, other_branch):
    murid = [{"v1": f"M{i:02d}", "nama": f"Murid {i:02d}", "std": f"STD-0000{i:02d}"} for i in range(1, 36)]
    make_rows(DMurid, branch, *murid)
    make_rows(StudentMaster, branch, *[{"std": m["std"], "nama": m["nama"], "st_base": "ACTIVE"} for m in murid])
    rows = []
    for i in range(1, 36):
        rows.append({"key": f"M{i:02d}|202608", "v1": f"M{i:02d}", "bulan": D(2026, 8, 1), "status": "Aktif", "grade": "Foundation 1.0",
                     "guru": "Ms. Linda", "guru_asli": "Linda", "tipe": "Partner", "mode": "Onsite"})
        rows.append({"key": f"M{i:02d}|202609", "v1": f"M{i:02d}", "bulan": D(2026, 9, 1), "status": "Off" if i <= 2 else "Aktif",
                     "grade": "Foundation 1.0", "guru": "Ms. Linda", "guru_asli": "Linda", "tipe": "Partner", "mode": "Onsite"})
    make_rows(DBulan, branch, *rows)
    make_rows(BukuKas, branch, {"bulan": D(2026, 9, 1), "tgl": D(2026, 9, 5), "jenis": "SPP", "nominal": 500000, "dihitung": "YA",
                                "ss1": "STD-000003", "sb1": 500000, "lid": "BK-1"})
    make_rows(DMurid, other_branch, {"v1": "X1", "nama": "Rahasia Cabang Lain", "std": "STD-000001"})


def get(client, **params):
    return client.get(URL, params)


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["CSO", "FINANCE", "ACADEMIC", "MANAGER", "BRANCH_ADMIN"])
def test_view_roles_see_the_report(client, branch, make_user, data, role):
    client.force_login(make_user(f"{role.lower()}@spi.test", role=role, branch=branch))
    response = get(client)
    body = response.content.decode()
    assert response.status_code == 200 and "Laporan Murid &amp; SPP" in body and "Rahasia Cabang Lain" not in body
    ctx = response.context
    assert ctx["f"].bulan == D(2026, 9, 1) and [c["value"] for c in ctx["murid_cards"][:2]] == ["33", "33"]
    assert ctx["spp_cards"][0]["value"] == "Rp 500.000" and ctx["spp_cards"][3]["value"] == "1  ·  3%"
    assert len(ctx["charts"]) == 7 and "Laporan Murid &amp; SPP" in body


@pytest.mark.django_db
def test_teacher_and_guest_cannot_open_it(client, branch, make_user):
    assert get(client).status_code == 302
    client.force_login(make_user("guru@spi.test", role="TEACHER", branch=branch, teacher_name="Mr. Uji"))
    assert get(client).status_code == 403


@pytest.mark.django_db
def test_htmx_gets_the_body_only_and_history_restore_gets_the_page(client, branch, make_user, data):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    part = client.get(URL, {"bulan": "2026-08"}, HTTP_HX_REQUEST="true")
    assert part.status_code == 200 and "<html" not in part.content.decode() and 'id="laporan-filter"' in part.content.decode()
    assert "HX-Request" in part["Vary"]
    full = client.get(URL, HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
    assert "<html" in full.content.decode()


@pytest.mark.django_db
def test_invalid_parameters_fall_back_to_defaults(client, branch, make_user, data):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    response = get(client, bulan="xx", program="Robotik", guru="<script>alert(1)</script>", daftar="apa", periode="2099-01")
    assert response.status_code == 200
    f = response.context["f"]
    assert (f.bulan, f.program, f.guru, response.context["daftar"]["key"]) == (D(2026, 9, 1), "Semua", "Semua", "")
    assert "<script>alert(1)</script>" not in response.content.decode()
    assert get(client, guru="ms. linda").context["f"].guru == "Ms. Linda"            # tanpa beda huruf -> nilai daftar


@pytest.mark.django_db
def test_student_list_shows_30_then_all_and_filters(client, branch, make_user, data):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    d = get(client).context["daftar"]
    assert (len(d["rows"]), d["total"], d["lebih"]) == (30, 35, True)
    assert len(get(client, daftar="semua").context["daftar"]["rows"]) == 35
    off = get(client, daftar="off-baru").context["daftar"]
    assert [r["nama"] for r in off["rows"]] == ["Murid 01", "Murid 02"] and off["judul"] == "Off baru"
    belum = get(client, daftar="belum-bayar").context["daftar"]
    assert belum["total"] == 32 and "Murid 03" not in [r["nama"] for r in belum["rows"]]


@pytest.mark.django_db
def test_months_before_the_cash_book_show_a_dash(client, branch, make_user, data):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    cards = get(client, bulan="2024-06").context["spp_cards"]
    assert [c["value"] for c in cards[:2]] == ["—", "—"] and cards[3]["value"] == "—" and cards[7]["soon"]


@pytest.mark.django_db
def test_undecided_august_journal_needs_a_decision(client, branch, make_user, data):
    BranchSetting.objects.create(branch=branch, key="jurnal_agu", value_text="BELUM DIPUTUSKAN")
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    ctx = get(client, bulan="2026-08").context
    assert ctx["spp_cards"][3]["value"] == "perlu keputusan" and ctx["spp_cards"][4]["value"] == "perlu keputusan"
    assert ctx["perhatian"][2]["catatan"] == "Agustus 2026: perlu keputusan jurnal (SETTINGS)"


@pytest.mark.django_db
def test_branch_without_data_renders(client, other_branch, make_user):
    StudentMaster.objects.all().delete()
    client.force_login(make_user("admin.as@spi.test", role="BRANCH_ADMIN", branch=other_branch))
    response = get(client)
    assert response.status_code == 200 and response.context["kosong"] and "Belum ada data murid" in response.content.decode()


@pytest.mark.django_db
def test_menu_links_to_the_report(client, branch, make_user):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    assert f'href="{reverse("dashboards:laporan")}"' in client.get("/").content.decode()
