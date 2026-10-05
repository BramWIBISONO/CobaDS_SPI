import datetime

import pytest
from django.urls import reverse

from classes import services
from classes.models import ClassMaster, ClassSchedule, Kehadiran, Sesi
from masterdata.models import TeacherMaster
from students.models import StudentMaster
from students.tests.factories import seed_branch

TODAY = datetime.date.today()


@pytest.fixture
def jkt(branch, other_branch):
    seed_branch(branch)
    ClassMaster.objects.create(branch=other_branch, row_no=1, class_id="CLS-P777", code="P777", tipe="Partner")
    return branch


def login(client, branch, make_user, role="ACADEMIC", **kw):
    user = make_user(f"{role.lower()}{len(kw)}@spi.test", role=role, branch=branch, **kw)
    client.force_login(user)
    return user


@pytest.mark.django_db
def test_class_list_detail_and_isolation(client, jkt, make_user):
    login(client, jkt, make_user)
    body = client.get(reverse("classes:list")).content.decode()
    assert "P001" in body and "F002" in body and "P777" not in body
    detail = client.get(reverse("classes:detail", args=["P001"])).content.decode()
    assert "Ani Wijaya" in detail and "Mr. Bram" in detail
    assert client.get(reverse("classes:detail", args=["P777"])).status_code == 404


@pytest.mark.django_db
def test_class_create_teacher_member_and_slot_flow(client, jkt, make_user):
    login(client, jkt, make_user)
    r = client.post(reverse("classes:create"), {"code": "G010", "tipe": "Group", "guru": "Ms. Linda", "mode": "OnSite"})
    assert r.status_code == 302 and ClassMaster.objects.filter(branch=jkt, code="G010").exists()
    bad = client.post(reverse("classes:create"), {"code": "X010", "tipe": "Group"})
    assert bad.status_code == 200 and "Huruf pertama" in bad.content.decode()
    assert client.post(reverse("classes:assign_teacher", args=["G010"]), {"guru": "Mr. Bram"}).status_code == 302
    assert ClassMaster.objects.get(branch=jkt, code="G010").guru == "Mr. Bram"
    assert client.post(reverse("classes:add_member", args=["G010"]), {"std": "STD-000001", "tanggal": TODAY.isoformat()}).status_code == 302
    assert StudentMaster.objects.get(branch=jkt, std="STD-000001").kode_in == "G010"
    r = client.post(reverse("classes:add_slot", args=["G010"]), {"day": "SENIN", "start": "15:00", "end": "16:00", "room": "Lab"})
    assert r.status_code == 302 and ClassSchedule.objects.filter(branch=jkt, code="G010").count() == 1


@pytest.mark.django_db
def test_finance_cannot_manage_classes(client, jkt, make_user):
    login(client, jkt, make_user, role="FINANCE")
    assert client.get(reverse("classes:list")).status_code == 200
    assert client.get(reverse("classes:create")).status_code == 403
    assert client.post(reverse("classes:assign_teacher", args=["P001"]), {"guru": "Ms. Linda"}).status_code == 403


@pytest.mark.django_db
def test_sessions_week_generate_and_record_attendance(client, jkt, make_user):
    user = login(client, jkt, make_user)
    monday = TODAY - datetime.timedelta(days=TODAY.weekday())
    services.add_slot(jkt, user, "P001", day="SENIN", start=datetime.time(15, 0), end=datetime.time(16, 0))
    r = client.post(reverse("classes:generate"), {"start": monday.isoformat(), "end": (monday + datetime.timedelta(days=6)).isoformat()})
    assert r.status_code == 302
    sid = f"SES-{monday:%Y%m%d}-SCH-APP-000001"
    body = client.get(reverse("classes:sessions"), {"minggu": monday.isoformat()}).content.decode()
    assert sid in body and "P001" in body
    page = client.get(reverse("classes:session", args=[sid])).content.decode()
    assert "Ani Wijaya" in page
    r = client.post(reverse("classes:session", args=[sid]), {"status": "REALIZED", "att_STD-000001": "HADIR", "catatan": "Loop for"})
    assert r.status_code == 302 and Kehadiran.objects.get(branch=jkt, sid=sid).status == "HADIR"
    assert Sesi.objects.get(branch=jkt, sid=sid).status == "REALIZED"
    assert "100%" in client.get(reverse("students:detail", args=["STD-000001"]), {"tab": "kehadiran"}).content.decode()


@pytest.mark.django_db
def test_teacher_sees_only_own_schedule_and_cannot_touch_others(client, jkt, make_user):
    admin = make_user("admin@spi.test", role="BRANCH_ADMIN", branch=jkt)
    monday = TODAY - datetime.timedelta(days=TODAY.weekday())
    services.add_slot(jkt, admin, "P001", day="SENIN", start=datetime.time(15, 0), end=datetime.time(16, 0))
    services.add_slot(jkt, admin, "F002", day="SENIN", start=datetime.time(17, 0), end=datetime.time(18, 0))
    services.generate_sessions(jkt, admin, monday, monday + datetime.timedelta(days=13))
    login(client, jkt, make_user, role="TEACHER", teacher_name="Mr. Bram")
    mine = client.get(reverse("classes:my_sessions")).content.decode()
    assert "P001" in mine and "F002" not in mine
    own = f"SES-{monday:%Y%m%d}-SCH-APP-000001"
    other = f"SES-{monday:%Y%m%d}-SCH-APP-000002"
    assert client.get(reverse("classes:session", args=[own])).status_code == 200
    assert client.get(reverse("classes:session", args=[other])).status_code == 403
    assert client.post(reverse("classes:session", args=[own]), {"status": "REALIZED", "att_STD-000001": "IZIN"}).status_code == 302
    assert client.get(reverse("classes:list")).status_code == 403 and client.get(reverse("students:list")).status_code == 403


@pytest.mark.django_db
def test_teacher_pages(client, jkt, make_user):
    login(client, jkt, make_user)
    body = client.get(reverse("masterdata:teachers")).content.decode()
    assert "Mr. Bram" in body and "Ms. Linda" in body
    assert "P001" in client.get(reverse("masterdata:teacher", args=["TCH-001"])).content.decode()
    r = client.post(reverse("masterdata:teacher_create"), {"name": "Ms. Rina", "status": "ACTIVE"})
    assert r.status_code == 302 and TeacherMaster.objects.filter(branch=jkt, name="Ms. Rina").exists()
