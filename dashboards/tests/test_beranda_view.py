import pytest
from django.urls import reverse

from dashboards.tests.helpers import make_rows
from students.models import StudentMaster


@pytest.fixture
def murid(branch, other_branch):
    make_rows(StudentMaster, branch, {"std": "STD-000001", "nama": "Ani Wijaya", "st_base": "ACTIVE", "kode_read": "P01"},
              {"std": "STD-000002", "nama": "Budi", "st_base": "ON LEAVE"})
    make_rows(StudentMaster, other_branch, {"std": "STD-000001", "nama": "Wira Cabang Lain", "st_base": "ACTIVE"})


@pytest.mark.django_db
def test_home_shows_colored_cards_with_excel_texts(client, branch, make_user, murid):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    body = client.get("/").content.decode()
    assert "Murid aktif (sekarang)" in body and "tone-murid" in body and "tone-spp" in body and "tone-kelas" in body
    assert "cuti 1  ·  pending 0  ·  status v4 (INPUT CENTER)" in body
    assert body.count("kpi-soon") == 3 and "buku kas belum ada" in body
    assert reverse("dashboards:cari") in body


@pytest.mark.django_db
def test_home_works_for_a_branch_without_data(client, other_branch, make_user):
    client.force_login(make_user("admin.as@spi.test", role="BRANCH_ADMIN", branch=other_branch))
    response = client.get("/")
    assert response.status_code == 200 and "riwayat DB Murid —" in response.content.decode()


@pytest.mark.django_db
def test_search_finds_students_of_the_active_branch_only(client, branch, make_user, murid):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    body = client.get(reverse("dashboards:cari"), {"q": "wi"}).content.decode()
    assert "Ani Wijaya" in body and "P01" in body and "Wira Cabang Lain" not in body and "<html" not in body
    empty = client.get(reverse("dashboards:cari"), {"q": "<script>x"}).content.decode()
    assert "<script>" not in empty and "Tidak ada murid" in empty


@pytest.mark.django_db
def test_search_is_closed_to_teachers_and_guests(client, branch, make_user):
    assert client.get(reverse("dashboards:cari"), {"q": "a"}).status_code == 302
    client.force_login(make_user("guru@spi.test", role="TEACHER", branch=branch, teacher_name="Mr. Uji"))
    assert client.get(reverse("dashboards:cari"), {"q": "a"}).status_code == 403
