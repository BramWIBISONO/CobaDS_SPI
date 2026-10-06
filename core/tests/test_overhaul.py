"""UI/UX overhaul: pencarian global, Command Center, kalender sesi (hari/minggu/bulan/tertunda), badge menu, UI Kit."""
import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from classes import calendar
from classes.models import ClassMaster, Sesi
from students.models import FollowUp, StudentMaster
from students.tests.factories import seed_branch

TODAY = timezone.localdate()


@pytest.fixture
def jkt(branch, other_branch):
    seed_branch(branch)
    StudentMaster.objects.create(branch=branch, row_no=3, std="STD-000003", nama="Citra Pending", st_base="PENDING")
    StudentMaster.objects.create(branch=other_branch, row_no=1, std="STD-000001", nama="Ani Cabang Lain", st_base="ACTIVE")
    ClassMaster.objects.create(branch=other_branch, row_no=1, class_id="CLS-P777", code="P777", tipe="Partner")
    return branch


def _session(branch, n, day, start, end, kode="P001", guru="Mr. Bram", status="SCHEDULED"):
    return Sesi.objects.create(branch=branch, row_no=n, sid=f"SES-{day:%Y%m%d}-X{n}", tgl=day, hari="", mulai=start, selesai=end,
                               kode=kode, guru=guru, status=status)


# ------------------------------------------------------------------ pencarian global

@pytest.mark.django_db
def test_global_search_finds_students_parents_classes_teachers_of_the_active_branch_only(client, jkt, make_user):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=jkt))
    body = client.get(reverse("core:search"), {"q": "ani"}).content.decode()
    assert "Ani Wijaya" in body and "Ani Cabang Lain" not in body and "<html" not in body
    assert reverse("students:detail", args=["STD-000001"]) in body and "?q=ani" in body
    assert "Ibu Sari" in client.get(reverse("core:search"), {"q": "sari"}).content.decode()
    assert "P001" in client.get(reverse("core:search"), {"q": "p00"}).content.decode()
    assert "P777" not in client.get(reverse("core:search"), {"q": "p77"}).content.decode()
    assert "Mr. Bram" in client.get(reverse("core:search"), {"q": "bram"}).content.decode()
    assert "minimal 2 huruf" in client.get(reverse("core:search"), {"q": "a"}).content.decode()
    nothing = client.get(reverse("core:search"), {"q": "<script>zz"}).content.decode()
    assert "<script>" not in nothing and "Tidak ada hasil" in nothing


@pytest.mark.django_db
def test_global_search_shows_only_modules_the_role_may_open(client, jkt, make_user):
    client.force_login(make_user("guru@spi.test", role="TEACHER", branch=jkt, teacher_name="Mr. Bram"))
    body = client.get(reverse("core:search"), {"q": "ani"}).content.decode()
    assert "Ani Wijaya" not in body                                   # guru tidak punya izin daftar murid
    assert client.get(reverse("core:search"), {"q": "ani"}).status_code == 200
    assert "data-global-search" not in client.get(reverse("classes:my_sessions")).content.decode()
    client.logout()
    assert client.get(reverse("core:search"), {"q": "ani"}).status_code == 302


# ------------------------------------------------------------------ Command Center

@pytest.mark.django_db
def test_command_center_lists_real_work_first(client, jkt, make_user):
    user = make_user("admin@spi.test", role="BRANCH_ADMIN", branch=jkt)
    _session(jkt, 1, TODAY - datetime.timedelta(days=3), datetime.time(15, 0), datetime.time(16, 0))
    FollowUp.objects.create(branch=jkt, row_no=1, fid="FU-000001", jenis="SPP", std="STD-000001", status="Terbuka",
                            next=TODAY - datetime.timedelta(days=2), aksi="Telepon orang tua")
    client.force_login(user)
    body = client.get("/").content.decode()
    assert "Perlu tindakan" in body
    assert "Sesi lampau belum dikonfirmasi" in body and "tampilan=tertunda" in body
    assert "Follow-up terlambat" in body and "Murid berstatus PENDING" in body
    assert body.index("Perlu tindakan") < body.index("Jadwal hari ini") < body.index("Murid aktif (sekarang)") < body.index("Aktivitas terbaru")
    assert "Semua beres" not in body


@pytest.mark.django_db
def test_command_center_today_schedule_and_empty_states(client, jkt, make_user):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=jkt))
    body = client.get("/").content.decode()
    assert "Tidak ada sesi hari ini" in body
    _session(jkt, 2, TODAY, datetime.time(0, 0), datetime.time(0, 1))           # sudah lewat jam selesai, belum dikonfirmasi
    body = client.get("/").content.decode()
    assert "Absensi hari ini belum selesai" in body and reverse("classes:session", args=[f"SES-{TODAY:%Y%m%d}-X2"]) in body


@pytest.mark.django_db
def test_activity_feed_hides_access_changes_without_audit_permission(client, jkt, make_user):
    from core import audit

    admin = make_user("admin@spi.test", role="BRANCH_ADMIN", branch=jkt)
    audit.log(branch=jkt, user=admin, action="ACCESS", entity="PENGGUNA", entity_id="rahasia@spi.test", new="Peran: CSO")
    audit.log(branch=jkt, user=admin, action="CREATE", entity="FOLLOW_UP", entity_id="FU-000009", new="Follow-up")
    client.force_login(make_user("cso@spi.test", role="CSO", branch=jkt))
    body = client.get("/").content.decode()
    assert "FU-000009" in body and "rahasia@spi.test" not in body
    client.force_login(admin)
    assert "rahasia@spi.test" in client.get("/").content.decode()


# ------------------------------------------------------------------ menu & kerangka

@pytest.mark.django_db
def test_menu_badges_count_overdue_work(client, jkt, make_user):
    _session(jkt, 3, TODAY - datetime.timedelta(days=1), datetime.time(15, 0), datetime.time(16, 0))
    FollowUp.objects.create(branch=jkt, row_no=2, fid="FU-000002", jenis="OFF", std="STD-000002", status="Terbuka", next=TODAY)
    FollowUp.objects.create(branch=jkt, row_no=3, fid="FU-000003", jenis="OFF", std="STD-000002", status="Selesai", next=TODAY)
    client.force_login(make_user("cso@spi.test", role="CSO", branch=jkt))
    body = client.get(reverse("students:list")).content.decode()
    assert 'aria-label="1 perlu tindakan"' in body and body.count("sb-badge is-alert") >= 2
    assert 'class="sb-link is-active"' in body and "Lewati ke konten" in body


@pytest.mark.django_db
def test_quick_actions_follow_permissions(client, jkt, make_user):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=jkt))
    body = client.get(reverse("students:list")).content.decode()
    assert reverse("students:create") in body and "Buat baru" in body
    client.force_login(make_user("fin@spi.test", role="FINANCE", branch=jkt))
    assert "Buat baru" not in client.get("/").content.decode()


@pytest.mark.django_db
def test_ui_kit_is_for_branch_admins(client, jkt, make_user):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=jkt))
    assert client.get(reverse("core:ui_kit")).status_code == 403
    client.force_login(make_user("admin@spi.test", role="BRANCH_ADMIN", branch=jkt))
    body = client.get(reverse("core:ui_kit")).content.decode()
    assert "Fondasi Keuangan" in body and "bukan data" in body and "pay-overdue" in body


# ------------------------------------------------------------------ kalender sesi

@pytest.mark.django_db
def test_calendar_day_week_month_and_pending_views(client, jkt, make_user):
    monday = TODAY - datetime.timedelta(days=TODAY.weekday())
    _session(jkt, 4, monday, datetime.time(15, 0), datetime.time(16, 0))
    _session(jkt, 5, monday - datetime.timedelta(days=7), datetime.time(9, 0), datetime.time(10, 0), kode="F002", guru="Ms. Linda")
    client.force_login(make_user("acad@spi.test", role="ACADEMIC", branch=jkt))
    url = reverse("classes:sessions")
    week = client.get(url, {"tanggal": monday.isoformat()}).content.decode()
    assert f"SES-{monday:%Y%m%d}-X4" in week and "cal-event ev-P" in week and 'aria-current="page">Minggu' in week.replace("\n", "").replace("  ", "")
    day = client.get(url, {"tampilan": "hari", "tanggal": monday.isoformat()}).content.decode()
    assert f"SES-{monday:%Y%m%d}-X4" in day and "is-day" in day
    month = client.get(url, {"tampilan": "bulan", "tanggal": monday.isoformat()}).content.decode()
    assert "month-cell" in month and "P001" in month
    pending = client.get(url, {"tampilan": "tertunda"}).content.decode()
    old = f"SES-{monday - datetime.timedelta(days=7):%Y%m%d}-X5"
    assert old in pending and "Sesi lampau belum dikonfirmasi" in pending
    assert client.get(url, {"tampilan": "tidak-ada", "tanggal": "bukan-tanggal"}).status_code == 200


def test_calendar_layout_places_overlaps_side_by_side():
    class S:
        def __init__(self, sid, a, b):
            self.sid, self.mulai, self.selesai, self.kode = sid, datetime.time(*a), datetime.time(*b), "P1"

    items = [{"s": S("a", (15, 0), (16, 0))}, {"s": S("b", (15, 30), (16, 30))}, {"s": S("c", (17, 0), (18, 0))}]
    placed, untimed = calendar.lay_out_day(items, 8)
    by = {it["s"].sid: it for it in placed}
    assert by["a"]["width"] == by["b"]["width"] == 50 and by["a"]["left"] == 0 and by["b"]["left"] == 50
    assert by["c"]["width"] == 100 and by["a"]["top"] == 7 * calendar.HOUR_PX and untimed == []
    assert calendar.hour_range([S("x", (7, 30), (21, 15))]) == (7, 22)
    assert calendar.shift_month(datetime.date(2026, 1, 31), 1) == datetime.date(2026, 2, 28)
