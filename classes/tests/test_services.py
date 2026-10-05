import datetime

import pytest
from django.core.exceptions import ValidationError

from audit.models import AuditLog
from branches.models import BranchSetting
from classes import services
from classes.models import ClassMaster, ClassSchedule, Kehadiran, Sesi
from masterdata import services as teachers
from masterdata.models import TeacherMaster
from students.models import StudentMaster
from students.tests.factories import open_period, seed_branch

D = datetime.date
TODAY = D(2026, 10, 5)                                     # Senin


@pytest.fixture
def jkt(branch):
    seed_branch(branch)
    return branch


@pytest.mark.django_db
def test_create_class_checks_code_type_and_duplicates(jkt, make_user):
    user = make_user("akad@spi.test", role="ACADEMIC", branch=jkt)
    c = services.create_class(jkt, user, code="G003", tipe="Group", program="Foundation", level="Foundation 1.0", guru="Ms. Linda",
                              mode="OnSite", start=TODAY)
    assert (c.class_id, c.code, c.guru) == ("CLS-G003", "G003", "Ms. Linda")
    with pytest.raises(ValidationError, match="sudah ada"):
        services.create_class(jkt, user, code="g003", tipe="Group")
    with pytest.raises(ValidationError, match="Huruf pertama"):
        services.create_class(jkt, user, code="P009", tipe="Focus")
    with pytest.raises(ValidationError, match="Guru"):
        services.create_class(jkt, user, code="P009", tipe="Partner", guru="Mr. Hantu")


@pytest.mark.django_db
def test_assign_teacher_follows_to_current_members(jkt, make_user):
    user = make_user("akad@spi.test", role="ACADEMIC", branch=jkt)
    services.assign_teacher(jkt, user, "P001", guru="Ms. Linda", today=TODAY)
    assert ClassMaster.objects.get(branch=jkt, code="P001").guru == "Ms. Linda"
    assert StudentMaster.objects.get(branch=jkt, std="STD-000001").guru_in == "Ms. Linda"
    assert AuditLog.objects.filter(branch=jkt, eid="CLS-P001", field="Guru").exists()


@pytest.mark.django_db
def test_close_class_only_without_active_students(jkt, make_user):
    user = make_user("akad@spi.test", role="ACADEMIC", branch=jkt)
    with pytest.raises(ValidationError, match="masih punya"):
        services.close_class(jkt, user, "P001", end=TODAY, today=TODAY)
    services.close_class(jkt, user, "F002", end=TODAY, today=TODAY)
    assert ClassMaster.objects.get(branch=jkt, code="F002").end == TODAY


@pytest.mark.django_db
def test_schedule_slots_and_session_generation_never_duplicate(jkt, make_user):
    user = make_user("akad@spi.test", role="ACADEMIC", branch=jkt)
    slot = services.add_slot(jkt, user, "P001", day="SENIN", start=datetime.time(15, 0), end=datetime.time(16, 0), room="Lab 1",
                             eff_from=D(2026, 10, 1))
    assert slot.sid == "SCH-APP-000001" and slot.teacher == "Mr. Bram"
    n = services.generate_sessions(jkt, user, D(2026, 10, 1), D(2026, 10, 31))
    assert n == 4 and services.generate_sessions(jkt, user, D(2026, 10, 1), D(2026, 10, 31)) == 0
    ses = Sesi.objects.get(branch=jkt, sid="SES-20261005-SCH-APP-000001")
    assert (ses.per, ses.hari, ses.kode, ses.guru, ses.status, ses.mulai) == ("2026-10", "SENIN", "P001", "Mr. Bram", "SCHEDULED", datetime.time(15, 0))
    services.end_slot(jkt, user, slot.sid, until=D(2026, 10, 12))
    assert services.generate_sessions(jkt, user, D(2026, 11, 1), D(2026, 11, 30)) == 0
    assert ClassSchedule.objects.get(branch=jkt, sid=slot.sid).eff_until == "2026-10-12"


@pytest.mark.django_db
def test_attendance_is_unique_per_student_and_updates_the_session(jkt, make_user):
    user = make_user("akad@spi.test", role="ACADEMIC", branch=jkt)
    services.add_slot(jkt, user, "P001", day="SENIN", start=datetime.time(15, 0), end=datetime.time(16, 0))
    services.generate_sessions(jkt, user, TODAY, TODAY)
    sid = "SES-20261005-SCH-APP-000001"
    assert [m["std"] for m in services.session_members(jkt, Sesi.objects.get(branch=jkt, sid=sid), TODAY)] == ["STD-000001"]
    services.record_session(jkt, user, sid, status="REALIZED", attendance={"STD-000001": "TERLAMBAT"}, catatan="Bab 3", today=TODAY)
    services.record_session(jkt, user, sid, status="REALIZED", attendance={"STD-000001": "HADIR"}, today=TODAY)
    rows = Kehadiran.objects.filter(branch=jkt, sid=sid)
    assert rows.count() == 1 and rows.get().status == "HADIR"
    ses = Sesi.objects.get(branch=jkt, sid=sid)
    assert (ses.status, ses.hadir, ses.absen, ses.konf_oleh) == ("REALIZED", 1, "", user.full_name) and "Bab 3" in ses.catatan
    assert AuditLog.objects.filter(branch=jkt, entity="KEHADIRAN", field="Status", old="TERLAMBAT", new="HADIR").exists()
    with pytest.raises(ValidationError, match="bukan anggota"):
        services.record_session(jkt, user, sid, status="REALIZED", attendance={"STD-000002": "HADIR"}, today=TODAY)


@pytest.mark.django_db
def test_teacher_can_record_only_own_sessions_and_closed_periods_are_locked(jkt, make_user):
    admin = make_user("akad@spi.test", role="ACADEMIC", branch=jkt)
    services.add_slot(jkt, admin, "P001", day="SENIN", start=datetime.time(15, 0), end=datetime.time(16, 0))
    services.generate_sessions(jkt, admin, D(2026, 9, 28), TODAY)
    linda = make_user("linda@spi.test", role="TEACHER", branch=jkt, teacher_name="Ms. Linda")
    bram = make_user("bram@spi.test", role="TEACHER", branch=jkt, teacher_name="BRAM")
    with pytest.raises(ValidationError, match="bukan sesi Anda"):
        services.record_session(jkt, linda, "SES-20261005-SCH-APP-000001", status="REALIZED", attendance={}, own_only=True, today=TODAY)
    services.record_session(jkt, bram, "SES-20261005-SCH-APP-000001", status="REALIZED", attendance={"STD-000001": "HADIR"},
                            own_only=True, today=TODAY)
    open_period(jkt, "2026-09", status="CLOSED")
    with pytest.raises(ValidationError, match="CLOSED"):
        services.record_session(jkt, admin, "SES-20260928-SCH-APP-000001", status="REALIZED", attendance={}, today=TODAY)


@pytest.mark.django_db
def test_attendance_rates(jkt, make_user):
    user = make_user("akad@spi.test", role="ACADEMIC", branch=jkt)
    services.add_slot(jkt, user, "P001", day="SENIN", start=datetime.time(15, 0), end=datetime.time(16, 0))
    services.generate_sessions(jkt, user, D(2026, 10, 1), D(2026, 10, 31))
    for day, st in ((5, "HADIR"), (12, "ABSEN"), (19, "TERLAMBAT"), (26, "IZIN")):
        services.record_session(jkt, user, f"SES-202610{day:02d}-SCH-APP-000001", status="REALIZED", attendance={"STD-000001": st},
                                today=D(2026, 10, 31))
    rate = services.attendance_rate(jkt, std="STD-000001")
    assert (rate["total"], rate["hadir"], rate["pct"]) == (4, 2, 50)
    assert services.attendance_rate(jkt, kode="P001")["pct"] == 50 and services.attendance_rate(jkt, std="STD-000002")["pct"] is None


@pytest.mark.django_db
def test_teacher_master_create_and_name_matching(jkt, make_user):
    user = make_user("akad@spi.test", role="ACADEMIC", branch=jkt)
    t = teachers.create_teacher(jkt, user, name="Ms. Rina", phone="0815", status="ACTIVE")
    assert t.tid == "TCH-APP-001" and TeacherMaster.objects.filter(branch=jkt, name="Ms. Rina").exists()
    with pytest.raises(ValidationError, match="sudah ada"):
        teachers.create_teacher(jkt, user, name="ms rina")
    assert teachers.teacher_key("Mr. Bram") == teachers.teacher_key("BRAM") == "bram"
    BranchSetting.objects.create(branch=jkt, key="P", value_number=4)
    summary = {r["t"].name: r for r in teachers.teacher_rows(jkt, TODAY)}
    assert summary["Mr. Bram"]["aktif"] == 1 and summary["Mr. Bram"]["kelas"] == 1
