import pytest
from django.urls import reverse

from core.branch_context import SESSION_KEY


@pytest.mark.django_db
def test_anonymous_user_is_sent_to_login(client):
    response = client.get("/")
    assert response.status_code == 302 and response.url.startswith("/akun/masuk/")


@pytest.mark.django_db
def test_user_without_branch_sees_no_access_page(client, make_user):
    client.force_login(make_user("baru@spi.test"))
    response = client.get("/")
    assert response.status_code == 200 and "belum punya akses" in response.content.decode()


@pytest.mark.django_db
def test_single_branch_is_selected_automatically_and_home_shows_counts(client, branch, make_user):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    response = client.get("/")
    body = response.content.decode()
    assert response.status_code == 200 and "SPI Jakarta" in body and "Murid" in body
    assert client.session[SESSION_KEY] == branch.pk


@pytest.mark.django_db
def test_switching_only_to_allowed_branches(client, branch, other_branch, make_user):
    user = make_user("mgr@spi.test", role="MANAGER", branch=branch)
    client.force_login(user)
    assert client.post(reverse("core:switch_branch"), {"branch": other_branch.pk}).status_code == 403
    from branches.models import Membership

    Membership.objects.create(user=user, branch=other_branch, role="CSO")
    assert client.get("/").status_code == 200                       # cabang pertama tetap aktif
    response = client.post(reverse("core:switch_branch"), {"branch": other_branch.pk, "next": "/"})
    assert response.status_code == 302 and client.session[SESSION_KEY] == other_branch.pk


@pytest.mark.django_db
def test_tampered_session_branch_is_ignored(client, branch, other_branch, make_user):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    session = client.session
    session[SESSION_KEY] = other_branch.pk
    session.save()
    client.get("/")
    assert client.session[SESSION_KEY] == branch.pk


@pytest.mark.django_db
def test_teacher_lands_on_own_schedule(client, branch, make_user):
    client.force_login(make_user("guru@spi.test", role="TEACHER", branch=branch, teacher_name="Mr. Uji"))
    response = client.get("/")
    assert response.status_code == 302 and response.url == "/jadwal-saya/"


@pytest.mark.django_db
def test_menu_shows_only_allowed_items(client, branch, make_user):
    client.force_login(make_user("admin@spi.test", role="BRANCH_ADMIN", branch=branch))
    assert "Pengguna &amp; Akses" in client.get("/").content.decode()
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    assert "Pengguna &amp; Akses" not in client.get("/").content.decode()
