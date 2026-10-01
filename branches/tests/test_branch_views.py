import datetime

import pytest
from django.urls import reverse

from branches.models import Branch
from masterdata.models import ProgramMaster

NEW = {"code": "spi-as", "name": "SPI Alam Sutera", "city": "Tangerang", "address": "", "status": "NEW_BRANCH",
       "language": "Indonesia", "currency": "IDR", "opening_date": "2026-11-01"}


@pytest.mark.django_db
def test_only_super_admin_manages_branches(client, branch, make_user):
    client.force_login(make_user("admin@spi.test", role="BRANCH_ADMIN", branch=branch))
    assert client.get(reverse("branches:list")).status_code == 403
    assert client.post(reverse("branches:list"), NEW).status_code == 403
    assert not Branch.objects.filter(code="SPI-AS").exists()


@pytest.mark.django_db
def test_super_admin_creates_the_first_branch_without_an_active_branch(client, make_user):
    client.force_login(make_user("boss@spi.test", super_admin=True))
    assert "Buat cabang pertama" in client.get("/").content.decode()
    assert "Buat cabang baru" in client.get(reverse("branches:list")).content.decode()
    response = client.post(reverse("branches:list"), NEW)
    assert response.status_code == 302
    branch = Branch.objects.get(code="SPI-AS")
    assert branch.opening_date == datetime.date(2026, 11, 1)
    assert ProgramMaster.objects.for_branch(branch).count() == 16
    assert client.get("/").status_code == 200                       # satu-satunya cabang langsung aktif


@pytest.mark.django_db
def test_branch_code_format_and_uniqueness(client, branch, make_user):
    client.force_login(make_user("boss@spi.test", super_admin=True))
    for code, message in (("AS", "Format Branch ID"), ("spi-jkt", "sudah dipakai")):
        response = client.post(reverse("branches:list"), {**NEW, "code": code})
        assert response.status_code == 200 and message in response.content.decode()
    assert Branch.objects.count() == 1
