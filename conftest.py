import pytest


@pytest.fixture(autouse=True)
def _fast_test_settings(settings):
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.WHITENOISE_AUTOREFRESH = True            # uji tidak menjalankan collectstatic (tanpa folder staticfiles/)
    from django.core.cache import cache

    cache.clear()


@pytest.fixture
def branch(db):
    from branches.models import Branch

    return Branch.objects.create(code="SPI-JKT", name="SPI Jakarta", city="Jakarta", status="ACTIVE")


@pytest.fixture
def other_branch(db):
    from branches.models import Branch

    return Branch.objects.create(code="SPI-AS", name="SPI Alam Sutera", city="Tangerang", status="ACTIVE")


@pytest.fixture
def make_user(db, django_user_model):
    from branches.models import Membership

    def make(email="user@spi.test", role=None, branch=None, super_admin=False, active=True, **kw):
        teacher_name = kw.pop("teacher_name", "")                     # milik Membership, bukan User
        user = django_user_model.objects.create_user(
            email, "Rahasia-12345", full_name=kw.pop("full_name", email.split("@")[0].title()),
            is_active=active, is_super_admin=super_admin, **kw)
        if role and branch:
            Membership.objects.create(user=user, branch=branch, role=role, teacher_name=teacher_name)
        return user

    return make
