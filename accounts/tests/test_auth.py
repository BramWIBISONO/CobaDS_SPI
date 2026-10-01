import re
from datetime import timedelta

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.tokens import email_verification_token

PASSWORD = "Sangat-Rahasia-2026"


def link_in(message, part):
    return re.search(r"https?://[^/\s]+(\S*" + re.escape(part) + r"\S*)", message.body).group(1)


def signup(client, email="budi@spi.test", password=PASSWORD):
    return client.post(reverse("accounts:signup"), {"full_name": "Budi Santoso", "email": email, "password1": password, "password2": password})


@pytest.mark.django_db
def test_signup_creates_an_inactive_user_and_sends_a_verification_link(client):
    response = signup(client)
    assert response.status_code == 302 and response.url == reverse("accounts:signup_done")
    user = User.objects.get(email="budi@spi.test")
    assert user.is_active is False and user.email_verified_at is None
    assert len(mail.outbox) == 1 and "/akun/verifikasi/" in mail.outbox[0].body


@pytest.mark.django_db
def test_same_email_in_other_case_does_not_create_a_second_account(client):
    signup(client)
    response = signup(client, email="BUDI@SPI.TEST")
    assert response.status_code == 302                                   # jawaban sama: tidak membocorkan email terdaftar
    assert User.objects.filter(email__iexact="budi@spi.test").count() == 1
    assert "sudah terdaftar" in mail.outbox[1].body


@pytest.mark.django_db
def test_cannot_log_in_before_verifying(client):
    signup(client)
    response = client.post(reverse("accounts:login"), {"email": "budi@spi.test", "password": PASSWORD})
    assert response.status_code == 200 and "belum diverifikasi" in response.content.decode()
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_verification_link_activates_once(client):
    signup(client)
    path = link_in(mail.outbox[0], "/akun/verifikasi/")
    assert client.get(path).status_code == 302
    user = User.objects.get(email="budi@spi.test")
    assert user.is_active and user.email_verified_at is not None
    assert client.get(path).status_code == 400                           # dipakai kedua kali: ditolak
    response = client.post(reverse("accounts:login"), {"email": "Budi@SPI.test", "password": PASSWORD})
    assert response.status_code == 302 and client.session["_auth_user_id"] == str(user.pk)


@pytest.mark.django_db
def test_expired_verification_link_is_refused(client, monkeypatch):
    signup(client)
    path = link_in(mail.outbox[0], "/akun/verifikasi/")
    later = timezone.now() + timedelta(days=2)
    monkeypatch.setattr(email_verification_token, "_now", lambda: later.replace(tzinfo=None))
    assert client.get(path).status_code == 400


@pytest.mark.django_db
def test_login_is_blocked_after_five_failures(client, make_user):
    make_user("fin@spi.test")
    for _ in range(5):
        client.post(reverse("accounts:login"), {"email": "fin@spi.test", "password": "salah-salah-salah"})
    response = client.post(reverse("accounts:login"), {"email": "fin@spi.test", "password": "Rahasia-12345"})
    assert "Terlalu banyak percobaan" in response.content.decode()
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_password_reset_flow(client, make_user):
    user = make_user("cso@spi.test")
    client.post(reverse("accounts:password_reset"), {"email": "CSO@spi.test"})
    assert len(mail.outbox) == 1
    path = link_in(mail.outbox[0], "/akun/reset/")
    response = client.get(path, follow=True)                             # Django menukar token dengan sesi, lalu form
    form_url = response.redirect_chain[-1][0]
    response = client.post(form_url, {"new_password1": "Password-Baru-2026", "new_password2": "Password-Baru-2026"})
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.check_password("Password-Baru-2026")


@pytest.mark.django_db
def test_password_reset_does_not_mail_unverified_accounts(client):
    signup(client)
    mail.outbox.clear()
    client.post(reverse("accounts:password_reset"), {"email": "budi@spi.test"})
    assert mail.outbox == []


@pytest.mark.django_db
def test_resend_gives_the_same_answer_for_unknown_emails(client):
    signup(client)
    a = client.post(reverse("accounts:resend"), {"email": "budi@spi.test"})
    b = client.post(reverse("accounts:resend"), {"email": "tidakada@spi.test"})
    assert a.status_code == b.status_code == 200
    assert len(mail.outbox) == 2                                         # pendaftaran + kirim ulang (tidak ada untuk email tak dikenal)


@pytest.mark.django_db
def test_logout_needs_post(client, make_user):
    client.force_login(make_user("x@spi.test"))
    assert client.get(reverse("accounts:logout")).status_code == 405
    assert client.post(reverse("accounts:logout")).status_code == 302
