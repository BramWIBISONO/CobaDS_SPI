import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse

from accounts.checks import demo_accounts_check
from accounts.demo import DEMO_USERS, ensure_password
from branches.models import Membership
from dashboards.tests.helpers import make_rows
from masterdata.models import TeacherMaster


@pytest.fixture
def demo(settings, tmp_path):
    settings.DEBUG = True
    settings.DEMO_ACCOUNTS = True
    settings.DEMO_PASSWORD = ""
    settings.ENV_FILE = tmp_path / ".env"
    settings.ENV_FILE.write_text("SECRET_KEY=x\n", encoding="utf-8")
    return settings


def test_demo_flag_without_debug_is_a_system_error(settings):
    settings.DEBUG, settings.DEMO_ACCOUNTS = False, True
    assert [e.id for e in demo_accounts_check(None)] == ["spi.E001"]
    settings.DEBUG = True
    assert demo_accounts_check(None) == []


def test_password_is_generated_once_into_the_env_file(demo):
    first = ensure_password(demo.ENV_FILE)
    assert len(first) >= 16 and f"DEMO_PASSWORD={first}" in demo.ENV_FILE.read_text(encoding="utf-8")
    assert ensure_password(demo.ENV_FILE) == first


@pytest.mark.django_db
def test_seed_creates_every_role_and_is_idempotent(demo, branch, other_branch, django_user_model):
    make_rows(TeacherMaster, branch, {"tid": "T-01", "name": "Ms. Linda"}, {"tid": "T-02", "name": "Mr. Bram"})
    call_command("seed_demo_accounts")
    call_command("seed_demo_accounts")
    users = django_user_model.objects.filter(email__endswith="@spi.local")
    assert users.count() == len(DEMO_USERS) == 8 and all(u.is_active and u.email_verified_at for u in users)
    assert users.get(email="superadmin@spi.local").is_super_admin
    roles = {(m.user.email, m.branch.code, m.role) for m in Membership.objects.select_related("user", "branch")}
    assert ("cso.jkt@spi.local", "SPI-JKT", "CSO") in roles and ("admin.as@spi.local", "SPI-AS", "BRANCH_ADMIN") in roles
    assert Membership.objects.get(user__email="guru.jkt@spi.local").teacher_name == "Ms. Linda"
    password = demo.ENV_FILE.read_text(encoding="utf-8").split("DEMO_PASSWORD=")[1].strip()
    assert users.get(email="finance.jkt@spi.local").check_password(password)


@pytest.mark.django_db
def test_seed_refuses_without_the_flags(settings):
    settings.DEBUG, settings.DEMO_ACCOUNTS = True, False
    with pytest.raises(CommandError, match="DEMO_ACCOUNTS"):
        call_command("seed_demo_accounts")


@pytest.mark.django_db
def test_login_panel_and_one_click_login(client, demo, branch, other_branch):
    call_command("seed_demo_accounts")
    page = client.get(reverse("accounts:login")).content.decode()
    password = demo.ENV_FILE.read_text(encoding="utf-8").split("DEMO_PASSWORD=")[1].strip()
    assert "Akun demo" in page and "cso.jkt@spi.local" in page and password not in page
    response = client.post(reverse("accounts:demo_login"), {"email": "cso.jkt@spi.local"})
    assert response.status_code == 302 and client.get("/").status_code == 200


@pytest.mark.django_db
def test_demo_login_is_closed_when_disabled_or_for_other_users(client, settings, make_user):
    make_user("bukan.demo@spi.test")
    settings.DEBUG, settings.DEMO_ACCOUNTS = True, False
    assert "Akun demo" not in client.get(reverse("accounts:login")).content.decode()
    assert client.post(reverse("accounts:demo_login"), {"email": "cso.jkt@spi.local"}).status_code == 404
    settings.DEMO_ACCOUNTS = True
    assert client.post(reverse("accounts:demo_login"), {"email": "bukan.demo@spi.test"}).status_code == 404
