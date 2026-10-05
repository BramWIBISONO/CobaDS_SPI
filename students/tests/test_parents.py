import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from audit.models import AuditLog
from students import parents
from students.models import ParentMaster, StudentMaster
from students.tests.factories import seed_branch


@pytest.fixture
def jkt(branch, other_branch):
    seed_branch(branch)
    ParentMaster.objects.create(branch=other_branch, row_no=1, pid="PAR-00001", nama="Orang Tua Cabang Lain")
    StudentMaster.objects.create(branch=other_branch, row_no=1, std="STD-000005", nama="Murid Cabang Lain")
    return branch


@pytest.mark.django_db
def test_create_update_and_link_children(jkt, make_user):
    user = make_user("cso@spi.test", role="CSO", branch=jkt)
    p = parents.create_parent(jkt, user, nama="Pak Dodi", hub="Ayah", wa="0811", email="dodi@contoh.id",
                              kontak_darurat="Bu Rina", telp_darurat="0812")
    assert p.pid == "PAR-00002" and p.sumber == "APLIKASI"
    parents.update_parent(jkt, user, p.pid, wa="0819", alamat="Jl. Melati 1")
    assert sorted(AuditLog.objects.filter(eid=p.pid, action="UPDATE").values_list("field", "new")) == [
        ("Alamat", "Jl. Melati 1"), ("WhatsApp", "0819")]
    parents.link_child(jkt, user, p.pid, "STD-000002")
    assert StudentMaster.objects.get(branch=jkt, std="STD-000002").par == p.pid
    with pytest.raises(ValidationError):
        parents.link_child(jkt, user, p.pid, "STD-000005")              # murid cabang lain
    parents.add_communication(jkt, user, p.pid, "Telepon: minta jadwal sabtu")
    assert "minta jadwal sabtu" in ParentMaster.objects.get(pk=p.pk).catatan
    with pytest.raises(ValidationError):
        parents.create_parent(jkt, user, nama="  ")


@pytest.mark.django_db
def test_parent_pages_respect_permissions_and_contacts(client, jkt, make_user):
    client.force_login(make_user("akad@spi.test", role="ACADEMIC", branch=jkt))
    body = client.get(reverse("students:parents")).content.decode()
    assert "Ibu Sari" in body and "Orang Tua Cabang Lain" not in body and "0812000001" not in body
    detail = client.get(reverse("students:parent_detail", args=["PAR-00001"])).content.decode()
    assert "Ani Wijaya" in detail and "sari@contoh.id" not in detail
    assert client.get(reverse("students:parent_create")).status_code == 403
    client.force_login(make_user("cso@spi.test", role="CSO", branch=jkt))
    detail = client.get(reverse("students:parent_detail", args=["PAR-00001"])).content.decode()
    assert "sari@contoh.id" in detail and "0812000001" in detail
    response = client.post(reverse("students:parent_create"), {"nama": "Pak Eko", "wa": "0815"})
    assert response.status_code == 302 and ParentMaster.objects.filter(branch=jkt, nama="Pak Eko").exists()
    response = client.post(reverse("students:parent_link", args=["PAR-00001"]), {"std": "STD-000002"})
    assert response.status_code == 302 and StudentMaster.objects.get(branch=jkt, std="STD-000002").par == "PAR-00001"
    assert client.get(reverse("students:parent_detail", args=["PAR-99999"])).status_code == 404
