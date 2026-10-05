import pytest
from django.urls import reverse

from audit.models import SecurityEvent


@pytest.mark.django_db
def test_login_logout_and_failed_login_are_recorded(client, make_user):
    make_user("staf@spi.test")
    client.post(reverse("accounts:login"), {"email": "staf@spi.test", "password": "salah-sekali-1"})
    client.post(reverse("accounts:login"), {"email": "staf@spi.test", "password": "Rahasia-12345"})
    client.post(reverse("accounts:logout"))
    rows = list(SecurityEvent.objects.order_by("pk").values_list("action", "email"))
    assert rows == [("LOGIN_GAGAL", "staf@spi.test"), ("LOGIN", "staf@spi.test"), ("LOGOUT", "staf@spi.test")]
    assert SecurityEvent.objects.filter(action="LOGIN").first().ip == "127.0.0.1"
