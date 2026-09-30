import pytest
from django.conf import settings
from django.db import connection


@pytest.mark.django_db
def test_database_is_postgresql():
    assert connection.vendor == "postgresql"


def test_timezone_and_language_follow_the_spec():
    assert settings.TIME_ZONE == "Asia/Jakarta"
    assert settings.LANGUAGE_CODE == "id"
    assert settings.USE_TZ is True


def test_argon2_is_the_production_hasher():
    from spi_web import settings as base

    assert base.PASSWORD_HASHERS[0].endswith("Argon2PasswordHasher")


@pytest.mark.django_db
def test_new_user_email_is_normalised_and_inactive(django_user_model):
    user = django_user_model.objects.create_user("Budi@Example.COM", "Rahasia-123456", full_name="Budi")
    assert user.email == "budi@example.com"
    assert user.is_active is False
    assert django_user_model.objects.get_by_natural_key("BUDI@example.com") == user
