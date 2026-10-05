import datetime

import pytest
from django.core.exceptions import ValidationError

from audit.models import AuditLog
from branches.models import BranchSetting
from classes.models import ClassMembers
from core.models import Notifikasi
from dashboards.calc.base import BranchData
from dashboards.calc.status import status_sekarang
from students import services
from students.models import CatatanMurid, FollowUp, ParentMaster, StatusEvent, StudentMaster, StudentOff
from students.tests.factories import open_period, seed_branch

D = datetime.date
TODAY = D(2026, 10, 5)


@pytest.fixture
def jkt(branch):
    seed_branch(branch)
    return branch


def status_now(branch, std):
    data = BranchData(branch, TODAY)
    return status_sekarang(data, next(s for s in data.students if s.std == std))


@pytest.mark.django_db
def test_create_student_writes_student_parent_status_event_and_audit(jkt, make_user):
    user = make_user("cso@spi.test", role="CSO", branch=jkt)
    s = services.create_student(jkt, user, nama="Citra Lestari", lahir=D(2015, 3, 2), hp="0819", program="Foundation",
                                level="Foundation 1.0", kode="F002", harga=600000, mulai=TODAY, status="ACTIVE",
                                ortu_nama="Pak Dodi", ortu_wa="0811", today=TODAY)
    assert s.std == "STD-000003" and (s.kode_in, s.guru_in, s.prog_in, s.harga_in) == ("F002", "Ms. Linda", "Foundation", 600000)
    parent = ParentMaster.objects.get(branch=jkt, pid=s.par)
    assert parent.pid == "PAR-00002" and parent.nama == "Pak Dodi" and parent.wa == "0811"
    ev = StatusEvent.objects.get(branch=jkt, std=s.std)
    assert (ev.status, ev.jenis, ev.tgl, ev.oleh) == ("ACTIVE", "MASUK", TODAY, user.full_name)
    assert status_now(jkt, s.std) == "ACTIVE"
    assert ClassMembers.objects.filter(branch=jkt, std=s.std, code="F002", status="CURRENT").exists()
    assert set(AuditLog.objects.filter(branch=jkt).values_list("entity", flat=True)) >= {"STUDENT_MASTER", "PARENT_MASTER", "STATUS_EVENT"}


@pytest.mark.django_db
def test_duplicate_student_is_refused_unless_confirmed(jkt, make_user):
    user = make_user("cso@spi.test", role="CSO", branch=jkt)
    services.create_student(jkt, user, nama="Dewi", lahir=D(2016, 1, 1), mulai=TODAY, status="PENDING", today=TODAY)
    with pytest.raises(services.DuplicateStudent):
        services.create_student(jkt, user, nama="  dewi ", lahir=D(2016, 1, 1), mulai=TODAY, status="PENDING", today=TODAY)
    s = services.create_student(jkt, user, nama="Dewi", lahir=D(2016, 1, 1), mulai=TODAY, status="PENDING", today=TODAY,
                                allow_duplicate=True)
    assert StudentMaster.objects.filter(branch=jkt, nama__iexact="dewi").count() == 2 and s.std == "STD-000004"


@pytest.mark.django_db
def test_parent_and_class_must_belong_to_the_same_branch(jkt, other_branch, make_user):
    seed_branch(other_branch)
    ParentMaster.objects.create(branch=other_branch, row_no=2, pid="PAR-00009", nama="Orang tua cabang lain")
    user = make_user("cso@spi.test", role="CSO", branch=jkt)
    with pytest.raises(ValidationError, match="Orang tua"):
        services.create_student(jkt, user, nama="Eka", ortu_pid="PAR-00009", mulai=TODAY, status="PENDING", today=TODAY)
    with pytest.raises(ValidationError, match="Kode kelas"):
        services.create_student(jkt, user, nama="Eka", kode="X999", mulai=TODAY, status="PENDING", today=TODAY)


@pytest.mark.django_db
def test_update_student_audits_only_changed_fields(jkt, make_user):
    user = make_user("cso@spi.test", role="CSO", branch=jkt)
    services.update_student(jkt, user, "STD-000001", nama="Ani W.", hp="0813111", sekolah="SD Harapan")
    rows = list(AuditLog.objects.filter(branch=jkt, eid="STD-000001").values_list("field", "old", "new"))
    assert sorted(rows) == [("Nama Murid", "Ani Wijaya", "Ani W."), ("Sekolah (ubah)", "", "SD Harapan")]


@pytest.mark.django_db
def test_status_change_to_off_and_back_keeps_full_history(jkt, make_user):
    user = make_user("cso@spi.test", role="CSO", branch=jkt)
    services.change_status(jkt, user, "STD-000001", status="OFF", tanggal=D(2026, 10, 2), alasan="Pindah kota",
                           kategori="Pindah domisili", today=TODAY)
    off = StudentOff.objects.get(branch=jkt, std="STD-000001")
    assert off.off_id == "OFF-000001-202610" and off.month == D(2026, 10, 1) and off.kode == "P001" and status_now(jkt, "STD-000001") == "OFF"
    services.change_status(jkt, user, "STD-000001", status="ACTIVE", tanggal=D(2026, 10, 4), alasan="Kembali", today=TODAY)
    jenis = list(StatusEvent.objects.filter(branch=jkt, std="STD-000001").order_by("tgl").values_list("status", "jenis"))
    assert jenis == [("OFF", "OFF"), ("ACTIVE", "AKTIF KEMBALI (REJOIN)")] and status_now(jkt, "STD-000001") == "ACTIVE"
    with pytest.raises(ValidationError, match="sudah"):
        services.change_status(jkt, user, "STD-000001", status="ACTIVE", tanggal=TODAY, today=TODAY)


@pytest.mark.django_db
def test_status_change_in_a_closed_period_is_refused(jkt, make_user):
    open_period(jkt, "2026-09", status="CLOSED")
    user = make_user("cso@spi.test", role="CSO", branch=jkt)
    with pytest.raises(ValidationError, match="CLOSED"):
        services.change_status(jkt, user, "STD-000001", status="ON LEAVE", tanggal=D(2026, 9, 20), today=TODAY)


@pytest.mark.django_db
def test_change_class_moves_membership_and_checks_capacity(jkt, make_user):
    BranchSetting.objects.create(branch=jkt, key="F", value_number=1)
    user = make_user("cso@spi.test", role="CSO", branch=jkt)
    services.change_class(jkt, user, "STD-000001", kode="F002", tanggal=TODAY, today=TODAY)
    s = StudentMaster.objects.get(branch=jkt, std="STD-000001")
    assert (s.kode_in, s.guru_in) == ("F002", "Ms. Linda")
    rows = dict(ClassMembers.objects.filter(branch=jkt, std="STD-000001").values_list("code", "status"))
    assert rows == {"P001": "ENDED", "F002": "CURRENT"}
    s2 = services.create_student(jkt, user, nama="Fajar", mulai=TODAY, status="ACTIVE", today=TODAY)
    with pytest.raises(services.ClassFull):
        services.change_class(jkt, user, s2.std, kode="F002", tanggal=TODAY, today=TODAY)
    services.change_class(jkt, user, s2.std, kode="F002", tanggal=TODAY, today=TODAY, allow_over_capacity=True)


@pytest.mark.django_db
def test_teacher_and_program_must_exist(jkt, make_user):
    user = make_user("cso@spi.test", role="CSO", branch=jkt)
    with pytest.raises(ValidationError, match="Guru"):
        services.change_teacher(jkt, user, "STD-000001", guru="Mr. Tidak Ada")
    services.change_teacher(jkt, user, "STD-000001", guru="ms. linda")
    assert StudentMaster.objects.get(branch=jkt, std="STD-000001").guru_in == "Ms. Linda"
    with pytest.raises(ValidationError, match="Level"):
        services.change_program(jkt, user, "STD-000001", program="Foundation", level="Development 2.1")
    services.change_program(jkt, user, "STD-000001", program="Foundation", level="Foundation 1.0")


@pytest.mark.django_db
def test_notes_and_follow_ups(jkt, make_user):
    user = make_user("cso@spi.test", role="CSO", branch=jkt)
    pic = make_user("pic@spi.test", role="CSO", branch=jkt)
    with pytest.raises(ValidationError):
        services.add_note(jkt, user, "STD-000001", "   ")
    services.add_note(jkt, user, "STD-000001", "Orang tua minta jadwal sore.")
    assert CatatanMurid.objects.get(branch=jkt, std="STD-000001").dibuat_oleh == user
    fu = services.create_followup(jkt, user, std="STD-000001", jenis="SPP", aksi="Hubungi orang tua", catatan="Tanya SPP Okt",
                                  jatuh_tempo=D(2026, 10, 7), prioritas="TINGGI", ditugaskan=pic, today=TODAY)
    assert fu.fid == "FU-000001" and fu.status == "Terbuka" and fu.ditugaskan == pic and fu.next == D(2026, 10, 7)
    assert Notifikasi.objects.filter(user=pic, branch=jkt, url__contains="/follow-up/").count() == 1
    services.update_followup(jkt, user, fu.fid, status="Selesai", catatan="Sudah bayar")
    fu = FollowUp.objects.get(pk=fu.pk)
    assert fu.status == "Selesai" and fu.selesai_pada is not None
