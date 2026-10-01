import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from importer.models import ImportRun
from importer.tests.factories import build_workbook
from students.models import StudentMaster

STUDENTS = {"STUDENT_MASTER": [{"Student ID": "STD-000001", "Nama Murid": "Ani"}]}


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture
def admin_client(client, branch, make_user):
    client.force_login(make_user("admin@spi.test", role="BRANCH_ADMIN", branch=branch))
    return client


def workbook_file(tmp_path, settings=None):
    return SimpleUploadedFile("jkt.xlsm", build_workbook(tmp_path / "wb.xlsx", STUDENTS, settings).read_bytes())


@pytest.mark.django_db
def test_only_branch_admin_can_import(client, branch, make_user):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    assert client.get(reverse("importer:upload")).status_code == 403


@pytest.mark.django_db
def test_upload_shows_a_preview_and_saves_nothing_until_confirmed(admin_client, tmp_path, branch):
    response = admin_client.post(reverse("importer:upload"), {"file": workbook_file(tmp_path)})
    run = ImportRun.objects.get()
    assert response.status_code == 302 and response.url == reverse("importer:preview", args=[run.pk])
    page = admin_client.get(response.url).content.decode()
    assert "STUDENT_MASTER" in page and "Simpan ke database" in page and "sudah berisi data" not in page
    assert not StudentMaster.objects.exists()
    page = admin_client.post(reverse("importer:commit", args=[run.pk]), follow=True).content.decode()
    assert "Tersimpan ke SPI Jakarta" in page
    assert StudentMaster.objects.for_branch(branch).count() == 1


@pytest.mark.django_db
def test_import_into_a_branch_with_data_needs_the_replace_checkbox(admin_client, tmp_path, branch):
    for _ in range(2):
        admin_client.post(reverse("importer:upload"), {"file": workbook_file(tmp_path)})
    first, second = ImportRun.objects.order_by("pk")
    admin_client.post(reverse("importer:commit", args=[first.pk]))
    assert "sudah berisi data" in admin_client.get(reverse("importer:preview", args=[second.pk])).content.decode()
    page = admin_client.post(reverse("importer:commit", args=[second.pk]), follow=True).content.decode()
    assert "ganti semua data cabang" in page
    second.refresh_from_db()
    assert second.status == "PREVIEW"
    admin_client.post(reverse("importer:commit", args=[second.pk]), {"replace": "on"})
    second.refresh_from_db()
    assert second.status == "COMMITTED" and StudentMaster.objects.for_branch(branch).count() == 1


@pytest.mark.django_db
def test_imports_of_another_branch_are_not_found(admin_client, other_branch):
    run = ImportRun.objects.create(branch=other_branch, original_name="as.xlsm", sha256="0" * 64, report={"ok": True})
    assert admin_client.get(reverse("importer:preview", args=[run.pk])).status_code == 404
    assert admin_client.post(reverse("importer:commit", args=[run.pk]), {"replace": "on"}).status_code == 404


@pytest.mark.django_db
def test_file_that_is_not_excel_is_refused_by_the_form(admin_client):
    response = admin_client.post(reverse("importer:upload"), {"file": SimpleUploadedFile("murid.csv", b"a,b")})
    assert response.status_code == 200 and "Pilih file Excel" in response.content.decode()
    assert not ImportRun.objects.exists()


@pytest.mark.django_db
def test_workbook_of_another_branch_shows_the_error_and_cannot_be_saved(admin_client, tmp_path):
    admin_client.post(reverse("importer:upload"), {"file": workbook_file(tmp_path, settings={"unit": "UNIT-AS"})})
    run = ImportRun.objects.get()
    page = admin_client.get(reverse("importer:preview", args=[run.pk])).content.decode()
    assert "bukan UNIT-JKT" in page and "Simpan ke database" not in page
    admin_client.post(reverse("importer:commit", args=[run.pk]))
    assert not StudentMaster.objects.exists()
