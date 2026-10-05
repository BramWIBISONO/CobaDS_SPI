import datetime

import pytest
from django.urls import reverse

from students.models import FollowUp, StatusEvent, StudentMaster
from students.tests.factories import seed_branch


@pytest.fixture
def jkt(branch, other_branch):
    seed_branch(branch)
    StudentMaster.objects.create(branch=other_branch, row_no=1, std="STD-000099", nama="Rahasia Cabang Lain", st_base="ACTIVE")
    return branch


def login(client, branch, make_user, role="CSO", email=None):
    user = make_user(email or f"{role.lower()}@spi.test", role=role, branch=branch)
    client.force_login(user)
    return user


@pytest.mark.django_db
def test_list_search_filter_sort_and_branch_isolation(client, jkt, make_user):
    login(client, jkt, make_user)
    body = client.get(reverse("students:list")).content.decode()
    assert "Ani Wijaya" in body and "Budi Santoso" in body and "Rahasia Cabang Lain" not in body
    assert "Budi" not in client.get(reverse("students:list"), {"status": "ACTIVE"}).content.decode()
    part = client.get(reverse("students:list"), {"q": "budi"}, HTTP_HX_REQUEST="true").content.decode()
    assert "<html" not in part and "Budi Santoso" in part and "Ani Wijaya" not in part
    ordered = client.get(reverse("students:list"), {"sort": "-nama"}).content.decode()
    assert ordered.index("Budi Santoso") < ordered.index("Ani Wijaya")


@pytest.mark.django_db
def test_list_and_profile_are_closed_to_teachers(client, jkt, make_user):
    login(client, jkt, make_user, role="TEACHER")
    assert client.get(reverse("students:list")).status_code == 403
    assert client.get(reverse("students:detail", args=["STD-000001"])).status_code == 403


@pytest.mark.django_db
def test_profile_tabs_and_contact_privacy(client, jkt, make_user):
    login(client, jkt, make_user, role="ACADEMIC")
    for tab in ("ringkasan", "status", "kelas", "akademik", "keuangan", "followup", "catatan", "riwayat", "tidak-ada"):
        assert client.get(reverse("students:detail", args=["STD-000001"]), {"tab": tab}).status_code == 200, tab
    body = client.get(reverse("students:detail", args=["STD-000001"])).content.decode()
    assert "Ani Wijaya" in body and "Ibu Sari" in body and "0812000001" not in body and "0813111" not in body
    assert client.get(reverse("students:detail", args=["STD-000099"])).status_code == 404


@pytest.mark.django_db
def test_profile_shows_contacts_to_cso(client, jkt, make_user):
    login(client, jkt, make_user)
    body = client.get(reverse("students:detail", args=["STD-000001"])).content.decode()
    assert "0812000001" in body and "0813111" in body


@pytest.mark.django_db
def test_create_student_through_the_form(client, jkt, make_user):
    login(client, jkt, make_user)
    form = {"nama": "Citra Lestari", "mulai": "2026-10-05", "status": "ACTIVE", "kode": "F002", "harga": "600000",
            "ortu_nama": "Pak Dodi", "ortu_wa": "0811"}
    response = client.post(reverse("students:create"), form)
    assert response.status_code == 302 and response.url == reverse("students:detail", args=["STD-000003"])
    again = client.post(reverse("students:create"), form)
    assert again.status_code == 200 and "Sudah ada murid bernama" in again.content.decode()
    bad = client.post(reverse("students:create"), {**form, "nama": "", "mulai": "kemarin"})
    assert bad.status_code == 200 and "Bidang ini tidak boleh kosong" in bad.content.decode() and "Masukkan tanggal yang valid" in bad.content.decode()


@pytest.mark.django_db
def test_finance_cannot_create_or_change_status(client, jkt, make_user):
    login(client, jkt, make_user, role="FINANCE")
    assert client.get(reverse("students:create")).status_code == 403
    assert client.post(reverse("students:status", args=["STD-000001"]), {"status": "OFF"}).status_code == 403


@pytest.mark.django_db
def test_status_change_page_requires_reason_for_off_and_creates_follow_up(client, jkt, make_user):
    login(client, jkt, make_user)
    url = reverse("students:status", args=["STD-000001"])
    missing = client.post(url, {"status": "OFF", "tanggal": "2026-10-05"})
    assert missing.status_code == 200 and "Alasan OFF wajib diisi" in missing.content.decode()
    ok = client.post(url, {"status": "OFF", "tanggal": "2026-10-05", "alasan": "Pindah kota", "buat_followup": "on", "konfirmasi": "on"})
    assert ok.status_code == 302 and StatusEvent.objects.filter(std="STD-000001", status="OFF").exists()
    assert FollowUp.objects.filter(std="STD-000001", jenis="OFF", status="Terbuka").exists()


@pytest.mark.django_db
def test_class_change_and_note(client, jkt, make_user):
    login(client, jkt, make_user)
    url = reverse("students:class", args=["STD-000001"])
    assert client.get(url).status_code == 200
    assert client.post(url, {"action": "kelas", "kode": "F002", "tanggal": "2026-10-05"}).status_code == 302
    assert StudentMaster.objects.get(branch=jkt, std="STD-000001").kode_in == "F002"
    assert client.post(reverse("students:note", args=["STD-000001"]), {"teks": "Minta jadwal sore"}).status_code == 302
    assert "Minta jadwal sore" in client.get(reverse("students:detail", args=["STD-000001"]), {"tab": "catatan"}).content.decode()


@pytest.mark.django_db
def test_export_has_no_contacts_and_bulk_follow_up(client, jkt, make_user):
    login(client, jkt, make_user)
    csv = client.get(reverse("students:export"), {"std": ["STD-000001"]}).content.decode("utf-8-sig")
    assert "Ani Wijaya" in csv and "Budi" not in csv and "0813111" not in csv
    response = client.post(reverse("students:bulk"), {"std": ["STD-000001", "STD-000002"], "jenis": "SPP", "prioritas": "NORMAL",
                                                      "aksi": "Kirim pengingat"})
    assert response.status_code == 302 and FollowUp.objects.filter(branch=jkt, jenis="SPP").count() == 2


@pytest.mark.django_db
def test_follow_up_list_detail_and_completion(client, jkt, make_user):
    me = login(client, jkt, make_user)
    client.post(reverse("students:followup_create"), {"std": "STD-000001", "jenis": "SPP", "prioritas": "TINGGI",
                                                      "jatuh_tempo": (datetime.date.today() - datetime.timedelta(days=1)).isoformat(),
                                                      "ditugaskan": me.pk})
    body = client.get(reverse("students:followups")).content.decode()
    assert "FU-000001" in body and "Terlambat" in body
    url = reverse("students:followup_detail", args=["FU-000001"])
    assert client.post(url, {"status": "Selesai", "prioritas": "TINGGI", "catatan": "Sudah bayar"}, follow=True).status_code == 200
    assert "FU-000001" not in client.get(reverse("students:followups")).content.decode()
    assert "FU-000001" in client.get(reverse("students:followups"), {"status": "semua"}).content.decode()
