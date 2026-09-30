# Tahap 1A — Fondasi: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Proyek Django `spi_web` dengan PostgreSQL lokal, semua tabel Excel v4 sebagai model per cabang, login lengkap (daftar, verifikasi email, masuk, lupa/reset password), cabang + peran + isolasi, audit & penomoran ID seperti VBA, impor workbook v4 (pratinjau → simpan) untuk Jakarta dan Alam Sutera, serta pembuatan cabang baru dari template.

**Architecture:** Definisi tabel diambil dari pipeline Excel (`v2_layout.py`) dan diekspor sekali ke `importer/schema/excel_tables.json`. Dari JSON itu dibangkitkan model Django (satu model per tabel Excel, kolom rumus tidak disimpan) dan importer generik membaca workbook lewat judul kolom yang sama. Setiap baris punya `branch`. Middleware memilih cabang aktif, dan hak akses dicek di server lewat matriks peran → kemampuan (spesifikasi §9).

**Tech Stack:** Python 3.12, Django 5.2 LTS, PostgreSQL 16 (pgserver untuk pengembangan), psycopg 3, django-environ, argon2-cffi, django-htmx, openpyxl, whitenoise, pytest + pytest-django, Tailwind CSS 4 (CLI via npm), HTMX, Alpine.js.

**Spec:** `docs/superpowers/specs/2026-09-30-spi-web-design.md`

## Global Constraints

- Semua kode di `C:\Users\SPI Workshop\Downloads\management excel\app web`; workbook di `..\APP` hanya dibaca, tidak pernah ditulis.
- Django 5.2 LTS (`Django==5.2.17`); PostgreSQL (bukan SQLite) untuk pengembangan, uji, dan produksi.
- `TIME_ZONE = "Asia/Jakarta"`, `LANGUAGE_CODE = "id"`, `USE_TZ = True`; teks tampilan berbahasa Indonesia.
- Hash password Argon2 (hasher pertama); login dengan email; akun baru tidak aktif sampai email diverifikasi dan tidak punya akses cabang sampai diberi peran.
- Setiap baris data Excel milik satu cabang (`branch`); kunci bisnis unik per cabang (kecuali IMPORT_LOG).
- Format ID sama dengan Excel; nomor berikutnya = nomor tertinggi + 1 per awalan per cabang, tidak pernah dipakai ulang, dibuat di dalam transaksi dengan kunci baris cabang.
- Kolom FORMULA Excel tidak disimpan; nilai tersimpan (ASLI, SEBAGIAN, SISTEM, TURUNAN, KOSONG, INPUT) disimpan apa adanya; kolom yang isinya campur angka/tanggal dan teks disimpan sebagai kolom bertipe + kolom `<nama>_text`.
- Angka disimpan sebagai `FloatField` (double, sama dengan Excel).
- Setiap perubahan oleh aplikasi tercatat di AUDIT_LOG (`LOG-000001`, "APLIKASI").
- K2: kontak tidak pernah ikut ekspor CSV (tidak ada ekspor di tahap ini). K3: tarif fee guru tidak dikarang.
- Perintah dijalankan dari folder `app web` dengan Git Bash; Python lewat `.venv/Scripts/python`.

## Cakupan

Tahap 1 di spesifikasi (§11) dipecah dua rencana: **1A (rencana ini)** = fondasi di atas; **1B** = perhitungan kolom rumus (status
sekarang, SPP, kelas, dsb.) dengan fixture emas dari nilai Excel, lalu halaman HOME / MURID / PROFIL yang sama dengan Excel.
Tidak termasuk 1A: form & halaman operasional (tahap 2), unggah buku kas bulanan (tahap 2), ekspor PDF / CSV dan deploy (tahap 3),
serta data pembanding SPP lama (D_SPPC, D_SPPDBM, keputusan CEK_NAMA) — diimpor bersama halaman CEK NAMA & pembanding SPP di tahap 3
sebagai tabel tambahan, tanpa mengganti data cabang lainnya.

## Review Focus

1. Workbook yang salah diunggah (v1/v2/v3, file bukan Excel, workbook cabang lain) → ditolak dengan pesan jelas; tidak ada yang tersimpan (Task 7, Task 8).
2. Impor kedua ke cabang yang sudah berisi data → diblokir kecuali "ganti semua" dicentang; penggantian atomik, tidak ada baris ganda (Task 8, Task 9).
3. Akses lintas cabang lewat URL / ID tebakan / session diubah → 403/404, cabang aktif kembali ke yang diizinkan (Task 5, Task 9).
4. Email ganda (beda huruf besar/kecil), login sebelum verifikasi, tautan verifikasi/reset kedaluwarsa atau dipakai dua kali → tidak ada akun ganda, tidak bisa masuk, tautan ditolak (Task 6).
5. Dua pengguna menyimpan bersamaan → ID tidak pernah sama (Task 4).

## File Structure

```
app web/
  .gitignore  .env.example  requirements.txt  requirements-dev.txt  pyproject.toml  manage.py  conftest.py  package.json  README.md
  scripts/devdb.py                 PostgreSQL tertanam (pgserver): start / stop, tulis DATABASE_URL ke .env
  spi_web/                         settings, urls, wsgi, asgi
  core/                            ExcelRow (model dasar), capabilities, branch_context, decorators, nav, ids, audit, beranda
  accounts/                        User, alur login/daftar/verifikasi/reset, admin pengguna & akses
  branches/                        Branch, Membership, BranchSetting, template_config.json, buat cabang
  masterdata/ students/ classes/ finance/ quality/ audit/   models_excel.py (DIBANGKITKAN) + models.py
  importer/                        schema/excel_tables.json, schema, reader, convert, validate, commit, services, ImportRun, UI, perintah
  tools/                           export_schema.py, generate_models.py, export_template_config.py (alat pengembang)
  templates/                       base.html, base_auth.html
  assets/                          app.css (input Tailwind), copy-vendor.mjs
  static/                          css/app.css (hasil build), vendor/htmx.min.js, vendor/alpine.min.js, img/spi-logo.png
```

---

### Task 1: Kerangka proyek, PostgreSQL tertanam, model User

**Files:**
- Create: `.gitignore`, `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `.env.example`, `manage.py`, `conftest.py`
- Create: `scripts/devdb.py`
- Create: `spi_web/__init__.py`, `spi_web/settings.py`, `spi_web/urls.py`, `spi_web/wsgi.py`, `spi_web/asgi.py`
- Create: `core/__init__.py`, `core/apps.py`, `core/tests/__init__.py`, `core/tests/test_smoke.py`
- Create: `accounts/__init__.py`, `accounts/apps.py`, `accounts/managers.py`, `accounts/models.py`, `accounts/tests/__init__.py`

**Interfaces:**
- Produces: `accounts.User` (`email`, `full_name`, `is_active`, `is_super_admin`, `email_verified_at`, `display_name`), `User.objects.create_user(email, password, **extra)`, `create_superuser(...)`; settings `SPI_EXCEL_DIR`, `LOGIN_MAX_ATTEMPTS`, `LOGIN_BLOCK_SECONDS`; fixture otomatis `_fast_test_settings`.

- [ ] **Step 1: File dasar proyek**

`.gitignore`:
```
__pycache__/
*.py[cod]
.venv/
.env
.devdb/
media/
staticfiles/
node_modules/
.pytest_cache/
```

`requirements.txt`:
```
Django==5.2.17
psycopg[binary]==3.3.6
django-environ==0.14.0
argon2-cffi==25.1.0
django-htmx==1.29.0
openpyxl==3.1.5
whitenoise==6.12.0
```

`requirements-dev.txt`:
```
-r requirements.txt
pytest>=8,<9
pytest-django==4.14.0
pgserver==0.1.4
```

`pyproject.toml`:
```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "spi_web.settings"
python_files = ["test_*.py"]
addopts = "-q -m 'not slow'"
markers = ["slow: memakai workbook Excel asli di ..\\APP (beberapa menit)"]
```

`.env.example`:
```
SECRET_KEY=ganti-dengan-kunci-acak-panjang
DEBUG=True
DATABASE_URL=postgres://postgres@127.0.0.1:5432/spi_web
ALLOWED_HOSTS=localhost,127.0.0.1
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=SPI Management <no-reply@localhost>
```

`manage.py`:
```python
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spi_web.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
```

`spi_web/__init__.py`: kosong.

`spi_web/wsgi.py`:
```python
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spi_web.settings")
application = get_wsgi_application()
```

`spi_web/asgi.py`:
```python
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spi_web.settings")
application = get_asgi_application()
```

`spi_web/urls.py`:
```python
urlpatterns = []
```

- [ ] **Step 2: Settings**

`spi_web/settings.py`:
```python
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
if (BASE_DIR / ".env").exists():
    environ.Env.read_env(str(BASE_DIR / ".env"))

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "core",
    "accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "spi_web.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "spi_web.wsgi.application"

DATABASES = {"default": env.db("DATABASE_URL")}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
     "OPTIONS": {"user_attributes": ("email", "full_name")}},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "/akun/masuk/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/akun/masuk/"
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24          # also the lifetime of an email-verification link
LOGIN_MAX_ATTEMPTS = 5
LOGIN_BLOCK_SECONDS = 15 * 60

LANGUAGE_CODE = "id"
TIME_ZONE = "Asia/Jakarta"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "media")))      # uploaded workbooks - never served publicly
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": env("STATICFILES_BACKEND", default="django.contrib.staticfiles.storage.StaticFilesStorage")},
}

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="SPI Management <no-reply@localhost>")

CACHES = {"default": {"BACKEND": "django.core.cache.backends.db.DatabaseCache", "LOCATION": "spi_cache"}}
SESSION_COOKIE_AGE = 60 * 60 * 12
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

SPI_EXCEL_DIR = Path(env("SPI_EXCEL_DIR", default=str(BASE_DIR.parent / "APP")))   # reference workbooks (read-only)
```

- [ ] **Step 3: Model User**

`core/__init__.py` dan `accounts/__init__.py`: kosong.

`core/apps.py`:
```python
from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "core"
    verbose_name = "Inti"
```

`accounts/apps.py`:
```python
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"
    verbose_name = "Akun"
```

`accounts/managers.py`:
```python
from django.contrib.auth.base_user import BaseUserManager
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email wajib diisi")
        user = self.model(email=self.normalize_email(email).strip().lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_active", True)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_super_admin", True)
        extra.setdefault("email_verified_at", timezone.now())
        return self.create_user(email, password, **extra)

    def get_by_natural_key(self, email):
        return self.get(email__iexact=email)
```

`accounts/models.py`:
```python
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField("Email", unique=True)
    full_name = models.CharField("Nama lengkap", max_length=150)
    is_active = models.BooleanField("Aktif", default=False, help_text="Aktif setelah email diverifikasi.")
    is_staff = models.BooleanField(default=False)
    is_super_admin = models.BooleanField("Super admin (semua cabang)", default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]
    objects = UserManager()

    class Meta:
        verbose_name = "Pengguna"
        verbose_name_plural = "Pengguna"

    def save(self, *args, **kwargs):
        self.email = (self.email or "").strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return self.full_name or self.email
```

`conftest.py`:
```python
import pytest


@pytest.fixture(autouse=True)
def _fast_test_settings(settings):
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    from django.core.cache import cache

    cache.clear()
```

- [ ] **Step 4: PostgreSQL tertanam**

`scripts/devdb.py`:
```python
"""Embedded PostgreSQL for development and tests (pip package pgserver: no installer, no admin rights).
    .venv/Scripts/python scripts/devdb.py start   start or reuse the server, create database spi_web, write DATABASE_URL to .env
    .venv/Scripts/python scripts/devdb.py stop
Data directory: .devdb/ (git-ignored). Its Windows short (8.3) path is used because PostgreSQL tools dislike spaces in paths."""
import ctypes
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

import pgserver

ROOT = Path(__file__).resolve().parent.parent
PGDATA = ROOT / ".devdb"
ENV = ROOT / ".env"
DB = "spi_web"


def short_path(path):
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform != "win32":
        return str(path)
    buf = ctypes.create_unicode_buffer(1024)
    n = ctypes.windll.kernel32.GetShortPathNameW(str(path), buf, 1024)
    return buf.value if n else str(path)


def django_url(uri):
    """pgserver URI -> postgres://user@host:port/db (a socket directory becomes a percent-encoded host)"""
    u = urlparse(uri)
    host = u.hostname or parse_qs(u.query).get("host", [""])[0]
    if "/" in host or "\\" in host:
        host = quote(host, safe="")
    port = f":{u.port}" if u.port else ""
    return f"postgres://{u.username or 'postgres'}@{host}{port}{u.path}"


def write_env(url):
    text = ENV.read_text(encoding="utf-8") if ENV.exists() else ""
    line = f"DATABASE_URL={url}"
    if re.search(r"(?m)^DATABASE_URL=", text):
        text = re.sub(r"(?m)^DATABASE_URL=.*$", line, text)
    else:
        text = (text.rstrip("\n") + "\n" + line + "\n").lstrip("\n")
    ENV.write_text(text, encoding="utf-8")


def main(cmd):
    srv = pgserver.get_server(short_path(PGDATA), cleanup_mode="stop" if cmd == "stop" else None)
    if cmd == "stop":
        srv.cleanup()
        print("PostgreSQL berhenti")
        return
    if DB not in srv.psql("SELECT datname FROM pg_database;"):
        srv.psql(f"CREATE DATABASE {DB};")
    url = django_url(srv.get_uri(DB))
    write_env(url)
    print(url)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "start")
```

- [ ] **Step 5: Lingkungan & database**

Run:
```bash
cd "/c/Users/SPI Workshop/Downloads/management excel/app web"
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
cp .env.example .env
.venv/Scripts/python -c "import secrets,re,pathlib; p=pathlib.Path('.env'); p.write_text(re.sub(r'(?m)^SECRET_KEY=.*$', 'SECRET_KEY='+secrets.token_urlsafe(50), p.read_text()))"
.venv/Scripts/python scripts/devdb.py start
```
Expected: baris terakhir mencetak `postgres://postgres@...:.../spi_web` dan `.env` berisi `DATABASE_URL` itu. Bila `get_uri`/`psql`/`cleanup` pgserver berbeda tanda tangannya, periksa dengan `.venv/Scripts/python -c "import pgserver, inspect; print(inspect.getsource(pgserver.PostgresServer))"` dan sesuaikan tiga panggilan itu saja.

- [ ] **Step 6: Tulis uji asap yang gagal**

`core/tests/__init__.py` dan `accounts/tests/__init__.py`: kosong.

`core/tests/test_smoke.py`:
```python
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
```

- [ ] **Step 7: Jalankan uji — harus gagal**

Run: `.venv/Scripts/python -m pytest core/tests/test_smoke.py`
Expected: FAIL (tabel `accounts_user` belum ada / migrasi belum dibuat).

- [ ] **Step 8: Migrasi & jalankan ulang**

Run:
```bash
.venv/Scripts/python manage.py makemigrations accounts
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py createcachetable
.venv/Scripts/python -m pytest core/tests/test_smoke.py
```
Expected: `4 passed`.

- [ ] **Step 9: Commit**

```bash
git add .gitignore requirements.txt requirements-dev.txt pyproject.toml .env.example manage.py conftest.py scripts spi_web core accounts
git commit -m "feat: kerangka Django, PostgreSQL tertanam, model User (email)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Cabang, keanggotaan, parameter SETTINGS, model dasar ExcelRow, matriks hak akses

**Files:**
- Create: `branches/__init__.py`, `branches/apps.py`, `branches/models.py`, `branches/tests/__init__.py`, `branches/tests/test_branches.py`
- Create: `core/models.py`, `core/capabilities.py`, `core/tests/test_capabilities.py`
- Modify: `spi_web/settings.py` (INSTALLED_APPS), `conftest.py` (fixture cabang & pengguna)

**Interfaces:**
- Consumes: `accounts.User` (Task 1).
- Produces:
  - `branches.models.Branch` (`code`, `name`, `city`, `address`, `status`, `language`, `currency`, `opening_date`, properti `unit_id`)
  - `branches.models.Membership` (`user`, `branch`, `role`, `teacher_name`, `created_by`; `ROLE_CHOICES`)
  - `branches.models.BranchSetting` (`branch`, `key`, `label`, `value_text`, `value_number`, `value_date`, `note`, `row_no`; properti `value`; `BranchSetting.split_value(v) -> dict`)
  - `core.models.ExcelRow` (abstrak: `branch`, `row_no`, `EXCEL_SHEET`, `EXCEL_KEY`; manager `objects.for_branch(branch)`)
  - `core.capabilities.Cap` (StrEnum), `ALL_CAPS`, `ROLE_CAPS`, `role_of(user, branch) -> str | None`, `caps_for(user, branch) -> frozenset`
  - fixture pytest `branch` (SPI-JKT), `other_branch` (SPI-AS), `make_user(email=..., role=None, branch=None, super_admin=False, active=True, **kw)`

- [ ] **Step 1: Tulis uji yang gagal**

`branches/__init__.py` dan `branches/tests/__init__.py`: kosong.

`branches/tests/test_branches.py`:
```python
import datetime

import pytest
from django.db import IntegrityError

from branches.models import Branch, BranchSetting, Membership


def test_unit_id_follows_the_branch_id():
    assert Branch(code="SPI-AS").unit_id == "UNIT-AS"
    assert Branch(code="SPI-JKT").unit_id == "UNIT-JKT"
    assert Branch(code="BDG").unit_id == "UNIT-BDG"


@pytest.mark.django_db
def test_one_membership_per_user_and_branch(branch, make_user):
    user = make_user("cso@spi.test", role="CSO", branch=branch)
    with pytest.raises(IntegrityError):
        Membership.objects.create(user=user, branch=branch, role="FINANCE")


@pytest.mark.parametrize("raw, expected", [
    (4, {"value_text": "", "value_number": 4.0, "value_date": None}),
    (datetime.datetime(2026, 10, 1, 0, 0), {"value_text": "", "value_number": None, "value_date": datetime.date(2026, 10, 1)}),
    ("SPI Jakarta", {"value_text": "SPI Jakarta", "value_number": None, "value_date": None}),
    (None, {"value_text": "", "value_number": None, "value_date": None}),
])
def test_setting_value_is_split_by_type(raw, expected):
    assert BranchSetting.split_value(raw) == expected


@pytest.mark.django_db
def test_setting_value_reads_back(branch):
    s = BranchSetting.objects.create(branch=branch, key="off_lama", **BranchSetting.split_value(3))
    assert s.value == 3.0
```

`core/tests/test_capabilities.py`:
```python
import pytest

from core.capabilities import ALL_CAPS, ROLE_CAPS, Cap, caps_for, role_of

# spesifikasi §9 - (kemampuan, peran yang boleh)
MATRIX = [
    (Cap.MANAGE_ALL, set()),
    (Cap.BRANCH_ADMIN, {"BRANCH_ADMIN"}),
    (Cap.VIEW, {"BRANCH_ADMIN", "MANAGER", "CSO", "FINANCE", "ACADEMIC"}),
    (Cap.STUDENT_WRITE, {"BRANCH_ADMIN", "MANAGER", "CSO"}),
    (Cap.DOCUMENT_WRITE, {"BRANCH_ADMIN", "MANAGER", "CSO", "ACADEMIC"}),
    (Cap.STATUS_CHANGE, {"BRANCH_ADMIN", "MANAGER", "CSO"}),
    (Cap.PAYMENT_EVIDENCE, {"BRANCH_ADMIN", "CSO", "FINANCE"}),
    (Cap.FINANCE_VERIFY, {"BRANCH_ADMIN", "FINANCE"}),
    (Cap.PERIOD_OPEN, {"BRANCH_ADMIN", "MANAGER", "FINANCE"}),
    (Cap.PERIOD_CLOSE, {"BRANCH_ADMIN", "MANAGER"}),
    (Cap.CLASS_WRITE, {"BRANCH_ADMIN", "MANAGER", "CSO", "ACADEMIC"}),
    (Cap.ACADEMIC_WRITE, {"BRANCH_ADMIN", "MANAGER", "ACADEMIC"}),
    (Cap.SESSION_WRITE, {"BRANCH_ADMIN", "MANAGER", "CSO", "ACADEMIC"}),
    (Cap.SESSION_WRITE_OWN, {"BRANCH_ADMIN", "TEACHER"}),
    (Cap.SEE_CONTACTS, {"BRANCH_ADMIN", "MANAGER", "CSO", "FINANCE"}),
    (Cap.DATA_VALIDATE, {"BRANCH_ADMIN", "MANAGER", "CSO", "FINANCE", "ACADEMIC"}),
]


@pytest.mark.parametrize("cap, roles", MATRIX)
def test_role_matrix_matches_the_spec(cap, roles):
    assert {r for r, caps in ROLE_CAPS.items() if cap in caps} == roles


def test_matrix_covers_every_capability():
    assert {c for c, _ in MATRIX} == set(ALL_CAPS)


@pytest.mark.django_db
def test_super_admin_has_everything_in_every_branch(branch, other_branch, make_user):
    boss = make_user("boss@spi.test", super_admin=True)
    assert role_of(boss, other_branch) == "SUPER_ADMIN"
    assert caps_for(boss, branch) == ALL_CAPS


@pytest.mark.django_db
def test_a_role_only_counts_in_its_own_branch(branch, other_branch, make_user):
    cso = make_user("cso@spi.test", role="CSO", branch=branch)
    assert Cap.STUDENT_WRITE in caps_for(cso, branch)
    assert caps_for(cso, other_branch) == frozenset()
    assert role_of(cso, other_branch) is None


@pytest.mark.django_db
def test_user_without_membership_or_branch_has_nothing(branch, make_user):
    newbie = make_user("baru@spi.test")
    assert caps_for(newbie, branch) == frozenset()
    assert caps_for(newbie, None) == frozenset()
```

Tambahkan ke `conftest.py` (di bawah fixture yang sudah ada):
```python
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
```

- [ ] **Step 2: Jalankan uji — harus gagal**

Run: `.venv/Scripts/python -m pytest branches core/tests/test_capabilities.py`
Expected: FAIL (`ModuleNotFoundError: No module named 'branches.models'` / `core.capabilities`).

- [ ] **Step 3: Implementasi**

`branches/apps.py`:
```python
from django.apps import AppConfig


class BranchesConfig(AppConfig):
    name = "branches"
    verbose_name = "Cabang"
```

`branches/models.py`:
```python
import datetime

from django.conf import settings
from django.db import models


class Branch(models.Model):
    STATUS_CHOICES = [("NEW_BRANCH", "NEW_BRANCH (belum beroperasi)"), ("ACTIVE", "ACTIVE"), ("INACTIVE", "INACTIVE")]
    code = models.CharField("Branch ID", max_length=20, unique=True, help_text="mis. SPI-AS")
    name = models.CharField("Nama cabang", max_length=100)
    city = models.CharField("Kota", max_length=100, blank=True)
    address = models.TextField("Alamat", blank=True)
    status = models.CharField("Status cabang", max_length=12, choices=STATUS_CHOICES, default="NEW_BRANCH")
    language = models.CharField("Bahasa utama", max_length=40, default="Indonesia")
    currency = models.CharField("Mata uang", max_length=8, default="IDR")
    opening_date = models.DateField("Tanggal buka cabang", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Cabang"
        verbose_name_plural = "Cabang"

    def __str__(self):
        return self.name

    @property
    def unit_id(self):
        """UNIT- + Branch ID tanpa 'SPI-' (SPI-AS -> UNIT-AS), sama dengan rumus SETTINGS 'Unit cabang ini' di Excel"""
        code = self.code or ""
        return "UNIT-" + (code[4:] if code.upper().startswith("SPI-") else code)


class Membership(models.Model):
    ROLE_CHOICES = [("BRANCH_ADMIN", "Branch Admin"), ("MANAGER", "Manager"), ("CSO", "CSO"),
                    ("FINANCE", "Finance"), ("ACADEMIC", "Academic"), ("TEACHER", "Teacher")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField("Peran", max_length=20, choices=ROLE_CHOICES)
    teacher_name = models.CharField("Nama guru (seperti di jadwal)", max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "branch"], name="uq_membership_user_branch")]

    def __str__(self):
        return f"{self.user} · {self.branch.code} · {self.role}"


class BranchSetting(models.Model):
    """Parameter SETTINGS Excel yang boleh diubah orang (kapasitas, batas OFF / cuti, jatuh tempo, teks nota, ...)."""
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="settings")
    key = models.CharField("Kunci", max_length=40)
    label = models.CharField("Parameter", max_length=200, blank=True)
    value_text = models.TextField(blank=True, default="")
    value_number = models.FloatField(null=True, blank=True)
    value_date = models.DateField(null=True, blank=True)
    note = models.TextField("Keterangan", blank=True, default="")
    row_no = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["row_no", "key"]
        constraints = [models.UniqueConstraint(fields=["branch", "key"], name="uq_branch_setting_key")]

    def __str__(self):
        return f"{self.branch.code} · {self.key}"

    @property
    def value(self):
        if self.value_number is not None:
            return self.value_number
        if self.value_date is not None:
            return self.value_date
        return self.value_text or None

    @staticmethod
    def split_value(v):
        if isinstance(v, bool):
            return {"value_text": "TRUE" if v else "FALSE", "value_number": None, "value_date": None}
        if isinstance(v, (int, float)):
            return {"value_text": "", "value_number": float(v), "value_date": None}
        if isinstance(v, datetime.datetime):
            return {"value_text": "", "value_number": None, "value_date": v.date()}
        if isinstance(v, datetime.date):
            return {"value_text": "", "value_number": None, "value_date": v}
        return {"value_text": "" if v is None else str(v), "value_number": None, "value_date": None}
```

`core/models.py`:
```python
from django.db import models


class BranchQuerySet(models.QuerySet):
    def for_branch(self, branch):
        return self.filter(branch=branch)


class ExcelRow(models.Model):
    """Satu baris tabel Excel v4. Setiap baris milik satu cabang; row_no menjaga urutan baris seperti di sheet."""
    EXCEL_SHEET = ""
    EXCEL_KEY = ""
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="+")
    row_no = models.PositiveIntegerField("Baris", default=0, db_index=True)

    objects = BranchQuerySet.as_manager()

    class Meta:
        abstract = True
        ordering = ["row_no", "pk"]

    def __str__(self):
        return str(getattr(self, self.EXCEL_KEY, "") or self.pk)
```

`core/capabilities.py`:
```python
"""Hak akses (spesifikasi §9): peran per cabang -> kemampuan. Dicek di server untuk setiap aksi."""
from enum import StrEnum


class Cap(StrEnum):
    MANAGE_ALL = "manage_all"              # semua cabang, buat cabang, pengguna semua cabang, konfigurasi SPI
    BRANCH_ADMIN = "branch_admin"          # pengguna & SETTINGS cabang, impor migrasi
    VIEW = "view"                          # semua halaman & laporan cabang, ekspor
    STUDENT_WRITE = "student_write"        # Murid Baru / Update Murid / Lead / Follow-up
    DOCUMENT_WRITE = "document_write"      # Dokumen
    STATUS_CHANGE = "status_change"        # Perubahan Status (cuti / OFF / aktif kembali)
    PAYMENT_EVIDENCE = "payment_evidence"  # bukti bayar (PB)
    FINANCE_VERIFY = "finance_verify"      # verifikasi, keputusan tagihan, koreksi periode kas, unggah kas, nota
    PERIOD_OPEN = "period_open"            # BULAN BARU
    PERIOD_CLOSE = "period_close"          # TUTUP BULAN
    CLASS_WRITE = "class_write"            # Guru & Kelas Baru, Jadwal, Simulasi
    ACADEMIC_WRITE = "academic_write"      # Akademik
    SESSION_WRITE = "session_write"        # realisasi pertemuan / kegiatan guru (semua sesi)
    SESSION_WRITE_OWN = "session_write_own"  # realisasi sesi milik guru itu sendiri
    SEE_CONTACTS = "see_contacts"          # kontak orang tua / murid
    DATA_VALIDATE = "data_validate"        # Data Quality, CEK NAMA, issue


ALL_CAPS = frozenset(Cap)
ROLE_CAPS = {
    "BRANCH_ADMIN": ALL_CAPS - {Cap.MANAGE_ALL},
    "MANAGER": frozenset({Cap.VIEW, Cap.STUDENT_WRITE, Cap.DOCUMENT_WRITE, Cap.STATUS_CHANGE, Cap.PERIOD_OPEN, Cap.PERIOD_CLOSE,
                          Cap.CLASS_WRITE, Cap.ACADEMIC_WRITE, Cap.SESSION_WRITE, Cap.SEE_CONTACTS, Cap.DATA_VALIDATE}),
    "CSO": frozenset({Cap.VIEW, Cap.STUDENT_WRITE, Cap.DOCUMENT_WRITE, Cap.STATUS_CHANGE, Cap.PAYMENT_EVIDENCE, Cap.CLASS_WRITE,
                      Cap.SESSION_WRITE, Cap.SEE_CONTACTS, Cap.DATA_VALIDATE}),
    "FINANCE": frozenset({Cap.VIEW, Cap.PAYMENT_EVIDENCE, Cap.FINANCE_VERIFY, Cap.PERIOD_OPEN, Cap.SEE_CONTACTS, Cap.DATA_VALIDATE}),
    "ACADEMIC": frozenset({Cap.VIEW, Cap.DOCUMENT_WRITE, Cap.CLASS_WRITE, Cap.ACADEMIC_WRITE, Cap.SESSION_WRITE, Cap.DATA_VALIDATE}),
    "TEACHER": frozenset({Cap.SESSION_WRITE_OWN}),
}
ROLE_LABELS = {"SUPER_ADMIN": "Super Admin", "BRANCH_ADMIN": "Branch Admin", "MANAGER": "Manager", "CSO": "CSO",
               "FINANCE": "Finance", "ACADEMIC": "Academic", "TEACHER": "Teacher"}


def role_of(user, branch):
    if branch is None or not getattr(user, "is_authenticated", False):
        return None
    if user.is_super_admin:
        return "SUPER_ADMIN"
    membership = user.memberships.filter(branch=branch).only("role").first()
    return membership.role if membership else None


def caps_for(user, branch):
    role = role_of(user, branch)
    if role == "SUPER_ADMIN":
        return ALL_CAPS
    return ROLE_CAPS.get(role, frozenset())
```

Modify `spi_web/settings.py` — `INSTALLED_APPS` menjadi:
```python
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "core",
    "accounts",
    "branches",
]
```

- [ ] **Step 4: Migrasi & jalankan uji**

Run:
```bash
.venv/Scripts/python manage.py makemigrations branches
.venv/Scripts/python manage.py migrate
.venv/Scripts/python -m pytest
```
Expected: semua lulus (uji asap, uji cabang, 16 baris matriks + 4 uji peran).

- [ ] **Step 5: Commit**

```bash
git add branches core conftest.py spi_web/settings.py
git commit -m "feat: cabang, keanggotaan, parameter SETTINGS, ExcelRow, matriks hak akses" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Skema tabel Excel → model Django (dibangkitkan)

**Files:**
- Create: `tools/export_schema.py`, `tools/generate_models.py`
- Create: `importer/__init__.py`, `importer/apps.py`, `importer/models.py` (kosong dulu), `importer/schema.py`, `importer/schema/excel_tables.json` (hasil ekspor)
- Create (per app `masterdata`, `students`, `classes`, `finance`, `quality`, `audit`): `__init__.py`, `apps.py`, `models.py`, `models_excel.py` (DIBANGKITKAN)
- Create: `importer/tests/__init__.py`, `importer/tests/test_schema_models.py`
- Modify: `spi_web/settings.py` (INSTALLED_APPS)

**Interfaces:**
- Consumes: `core.models.ExcelRow` (Task 2); pipeline `..\00_SYSTEM\APP_BUILD_V2\_scripts\v2_layout.py` dan workbook Jakarta (hanya dibaca, hanya oleh `tools/export_schema.py`).
- Produces:
  - `importer.schema.FieldSpec(header, name, avail, kind, stored, text_field, aliases)`; `kind` ∈ `text | number | date | datetime | time | bool`
  - `importer.schema.TableSpec(sheet, app, model, header_row, data_row, key, unique, skip_key_only, stop_at_blank, fields)` dengan `stored_fields`, `field_by_header`, `field_by_name`, `model_class()`
  - `importer.schema.load_schema() -> tuple[TableSpec, ...]`, `importer.schema.table(sheet) -> TableSpec`
  - 34 model: nama = sheet dalam CamelCase (`STUDENT_MASTER` → `students.StudentMaster`, `BUKU_KAS_KELUAR` → `finance.BukuKasKeluar`, `CLASS_MEMBERS` → `classes.ClassMembers`, `D_BULAN` → `students.DBulan`, `D_MURID` → `students.DMurid`, `AUDIT_LOG` → `audit.AuditLog`, `IMPORT_LOG` → `audit.ImportLog`); nama field = kunci kolom di `v2_layout.py` (mis. `std`, `nama`, `par`, `lid`, `ts`).

- [ ] **Step 1: Alat ekspor skema**

`tools/export_schema.py`:
```python
"""Ekspor definisi tabel Excel v4 ke importer/schema/excel_tables.json (dijalankan sekali, hanya membaca).

Tata letak tabel = v2_layout.py pipeline (judul kolom, kunci, jenis kolom, format angka). Jenis nilai (text / number / date / datetime /
time / bool) ditentukan dari format; bila kolom tidak berformat tanggal/angka, dari nilai di workbook Jakarta. Kolom yang isinya campur
(angka/tanggal + teks) mendapat kolom pendamping <nama>_text. Sheet staging D_BULAN / D_MURID (judul di baris 3) dibaca dari workbook;
kolom rumusnya dikenali dari selnya.
    .venv/Scripts/python tools/export_schema.py
"""
import datetime
import json
import keyword
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl

WEB = Path(__file__).resolve().parent.parent
MGMT = WEB.parent
PIPE = MGMT / "00_SYSTEM" / "APP_BUILD_V2" / "_scripts"
JKT = MGMT / "APP" / "SPI_STUDENT-SPP_APP_2026_09_v4.xlsm"
OUT = WEB / "importer" / "schema" / "excel_tables.json"
sys.path.insert(0, str(PIPE))
import v2_layout as LY  # noqa: E402

APP_OF = {
    "PROGRAM_MASTER": "masterdata", "OFF_REASON_MASTER": "masterdata", "TARIF_FEE": "masterdata", "UNIT_MASTER": "masterdata",
    "TEACHER_MASTER": "masterdata", "ROOM_MASTER": "masterdata", "PARTNER_MASTER": "masterdata",
    "STUDENT_MASTER": "students", "PARENT_MASTER": "students", "STATUS_EVENT": "students", "STUDENT_OFF": "students",
    "FOLLOW_UP": "students", "ACADEMIC_RECORD": "students", "DOKUMEN": "students", "LEAD": "students",
    "STUDENT_ID_MAPPING": "students", "D_BULAN": "students", "D_MURID": "students",
    "CLASS_MASTER": "classes", "CLASS_MEMBERS": "classes", "CLASS_SCHEDULE": "classes", "SESI": "classes", "SIMULASI_JADWAL": "classes",
    "PERIODE": "finance", "SPP_TAGIHAN": "finance", "BUKTI_BAYAR": "finance", "BUKU_KAS": "finance", "BUKU_KAS_KELUAR": "finance",
    "PEMBAYAR": "finance", "NOTA_LOG": "finance",
    "ISSUE_UNIT": "quality",
    "AUDIT_LOG": "audit", "IMPORT_LOG": "audit", "SOURCE_REFERENCE": "audit",
}
STAGING = {
    "D_BULAN": {"header_row": 3, "key_header": "Kunci (ID|yyyymm)", "aliases": {},
                "names": {"Kunci (ID|yyyymm)": "key", "ID": "v1", "Nama Murid": "nama", "Bulan": "bulan", "Status": "status",
                          "Tanggal status": "tgl_status", "Keterangan": "ket", "Level (Grade)": "grade", "Program": "program",
                          "Guru (asli)": "guru_asli", "Guru (rapi)": "guru", "Tipe Kelas": "tipe", "Mode": "mode", "Kelompok": "kelompok",
                          "Sumber (sel asli)": "sumber", "Student ID": "std", "Kode Kelas (bulan itu)": "kode_bulan",
                          "Kode Kelas (terakhir, DB Murid)": "kode_terakhir", "Sumber Kode Kelas": "kode_sumber", "Sekolah": "sekolah",
                          "Issue Terbuka (bulan ini)": "issues", "Import Batch": "batch"}},
    "D_MURID": {"header_row": 3, "key_header": "ID", "names": {"ID": "v1", "Student ID": "std", "Nama Murid": "nama"},
                "aliases": {"Baris di DB Murid JKT": ["Baris di DB Murid cabang"]}},
}
NON_UNIQUE = {"IMPORT_LOG"}                       # satu batch = beberapa baris (satu per file)
SKIP_KEY_ONLY = {"SIMULASI_JADWAL"}               # baris bernomor tanpa isi
STOP_AT_BLANK = {"SIMULASI_JADWAL"}               # blok 20 baris simulasi; di bawahnya tampilan JADWAL RESMI (bukan data)
KIND_OVERRIDES = {("SESI", "hadir"): "number"}    # tabel kosong di Jakarta: jenis tidak bisa dibaca dari data
for _k in ("lid", "user", "action", "entity", "eid", "field", "old", "new", "by"):
    KIND_OVERRIDES[("AUDIT_LOG", _k)] = "text"
for _k in ("batch", "date", "file", "path", "sha", "sheets", "rows", "excluded", "ver", "notes"):
    KIND_OVERRIDES[("IMPORT_LOG", _k)] = "text"
RESERVED = {"id", "pk", "branch", "row_no", "objects", "save", "delete", "clean", "check", "full_clean"}


def model_name(sheet):
    return {"D_BULAN": "DBulan", "D_MURID": "DMurid"}.get(sheet) or "".join(p.capitalize() for p in sheet.lower().split("_"))


def safe(name):
    name = re.sub(r"\W+", "_", name).strip("_").lower() or "kolom"
    if name[0].isdigit():
        name = "k_" + name
    if keyword.iskeyword(name) or name in RESERVED:
        name += "_x"
    return name


def kind_from_fmt(fmt):
    if not fmt:
        return None
    f = fmt.lower()
    if "hh" in f and ("dd" in f or "yy" in f):
        return "datetime"
    if "hh" in f:
        return "time"
    if "dd" in f or "yy" in f or "mmm" in f:
        return "date"
    if "0" in f or "#" in f:
        return "number"
    return None


def tag(v):
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int, float)):
        return "number"
    if isinstance(v, datetime.datetime):
        return "datetime" if (v.hour, v.minute, v.second) != (0, 0, 0) else "date"
    if isinstance(v, datetime.date):
        return "date"
    if isinstance(v, datetime.time):
        return "time"
    return "text"


def decide(fmt, found):
    kind = kind_from_fmt(fmt)
    if kind is None:
        kind = next((k for k in ("datetime", "date", "time", "number", "bool") if k in found), "text")
    if kind == "date" and "datetime" in found:
        kind = "datetime"
    return kind, (kind != "text" and "text" in found)


def sample(ws, header_row, key_idx):
    out = defaultdict(Counter)
    for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
        if key_idx >= len(row) or row[key_idx] in (None, ""):
            continue
        for i, v in enumerate(row):
            if v not in (None, ""):
                out[i][tag(v)] += 1
    return out


def header_list(ws, row):
    cells = next(ws.iter_rows(min_row=row, max_row=row, values_only=True), ())
    return [str(h).strip() if h is not None else "" for h in cells]


def layout_tables(wb):
    out = []
    for sheet, t in LY.TABLES.items():
        if sheet == "SETTINGS":
            continue                                  # branches.BranchSetting + identitas Branch
        ws = wb[sheet]
        hdr = header_list(ws, LY.HDR)
        tags = sample(ws, LY.HDR, hdr.index(t["key"]))
        fields, names, key_name = [], set(), None
        for header, key, avail, _d, _s, _w, fmt, _h in t["cols"]:
            name = safe(key)
            assert name not in names, (sheet, name)
            names.add(name)
            i = hdr.index(header) if header in hdr else None
            kind, mixed = decide(fmt, set(tags.get(i, {})) if i is not None else set())
            kind = KIND_OVERRIDES.get((sheet, key), kind)
            mixed = mixed and kind != "text"
            stored = avail != "FORMULA"
            fields.append({"header": header, "name": name, "avail": avail, "kind": kind, "stored": stored,
                           "text_field": f"{name}_text" if (stored and mixed) else None, "aliases": []})
            if header == t["key"]:
                key_name = name
        out.append({"sheet": sheet, "app": APP_OF[sheet], "model": model_name(sheet), "header_row": LY.HDR, "data_row": LY.D0,
                    "key": key_name, "unique": sheet not in NON_UNIQUE, "skip_key_only": sheet in SKIP_KEY_ONLY,
                    "stop_at_blank": sheet in STOP_AT_BLANK, "fields": fields})
    return out


def staging_tables(wb, wbf):
    out = []
    for sheet, cfg in STAGING.items():
        hr = cfg["header_row"]
        hdr = header_list(wb[sheet], hr)
        hdr = hdr[:max(i for i, h in enumerate(hdr) if h) + 1]
        tags = sample(wb[sheet], hr, hdr.index(cfg["key_header"]))
        formula_cols = set()
        for row in wbf[sheet].iter_rows(min_row=hr + 1, max_row=hr + 200, values_only=True):
            formula_cols |= {i for i, v in enumerate(row[:len(hdr)]) if isinstance(v, str) and v.startswith("=")}
        fields, names = [], set()
        for i, header in enumerate(hdr):
            if not header:
                continue
            name = base = safe(cfg["names"].get(header, header))
            n = 2
            while name in names:
                name, n = f"{base}_{n}", n + 1
            names.add(name)
            stored = i not in formula_cols
            kind, mixed = decide(None, set(tags.get(i, {})))
            fields.append({"header": header, "name": name, "avail": "ASLI" if stored else "FORMULA", "kind": kind, "stored": stored,
                           "text_field": f"{name}_text" if (stored and mixed) else None, "aliases": cfg["aliases"].get(header, [])})
        out.append({"sheet": sheet, "app": APP_OF[sheet], "model": model_name(sheet), "header_row": hr, "data_row": hr + 1,
                    "key": safe(cfg["names"].get(cfg["key_header"], cfg["key_header"])), "unique": True, "skip_key_only": False,
                    "stop_at_blank": False,
                    "fields": fields})
    return out


def main():
    wb = openpyxl.load_workbook(JKT, read_only=True, data_only=True)
    wbf = openpyxl.load_workbook(JKT, read_only=True, data_only=False)
    tables = layout_tables(wb) + staging_tables(wb, wbf)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"version": 1, "source": {"layout": "00_SYSTEM/APP_BUILD_V2/_scripts/v2_layout.py", "workbook": JKT.name},
                               "tables": tables}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("tabel", len(tables), "| kolom tersimpan", sum(1 for t in tables for f in t["fields"] if f["stored"]),
          "| kolom campur", [(t["sheet"], f["header"]) for t in tables for f in t["fields"] if f["text_field"]])


if __name__ == "__main__":
    main()
```

Run: `.venv/Scripts/python tools/export_schema.py`
Expected: `tabel 34 | ...`; daftar kolom campur memuat setidaknya `('STUDENT_MASTER', 'Join')`, `('STUDENT_MASTER', 'Harga SPP')`, `('STUDENT_OFF', 'Tanggal Off')`, `('STUDENT_OFF', 'Tanggal Join')`, `('CLASS_MEMBERS', 'Join Date')`.

- [ ] **Step 2: Pembaca skema + uji yang gagal**

`importer/__init__.py`, `importer/models.py`, `importer/tests/__init__.py`: kosong.

`importer/apps.py`:
```python
from django.apps import AppConfig


class ImporterConfig(AppConfig):
    name = "importer"
    verbose_name = "Impor data"
```

`importer/schema.py`:
```python
"""Definisi tabel Excel v4 (importer/schema/excel_tables.json, dibuat tools/export_schema.py)."""
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from django.apps import apps

SCHEMA_PATH = Path(__file__).resolve().parent / "schema" / "excel_tables.json"


@dataclass(frozen=True)
class FieldSpec:
    header: str
    name: str
    avail: str
    kind: str
    stored: bool
    text_field: str | None
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class TableSpec:
    sheet: str
    app: str
    model: str
    header_row: int
    data_row: int
    key: str
    unique: bool
    skip_key_only: bool
    stop_at_blank: bool
    fields: tuple[FieldSpec, ...]

    @property
    def stored_fields(self):
        return tuple(f for f in self.fields if f.stored)

    @property
    def field_by_header(self):
        return {f.header: f for f in self.fields}

    @property
    def field_by_name(self):
        return {f.name: f for f in self.fields}

    def model_class(self):
        return apps.get_model(self.app, self.model)


@lru_cache(maxsize=1)
def load_schema():
    data = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return tuple(
        TableSpec(**{**t, "fields": tuple(FieldSpec(**{**f, "aliases": tuple(f.get("aliases", ()))}) for f in t["fields"])})
        for t in data["tables"])


def table(sheet):
    return next(t for t in load_schema() if t.sheet == sheet)
```

`importer/tests/test_schema_models.py`:
```python
from django.db import models

from importer.schema import load_schema, table

KIND_FIELD = {"text": models.TextField, "number": models.FloatField, "date": models.DateField,
              "datetime": models.DateTimeField, "time": models.TimeField, "bool": models.BooleanField}


def test_34_tables_without_settings():
    sheets = [t.sheet for t in load_schema()]
    assert len(sheets) == 34 and "SETTINGS" not in sheets
    assert {"D_BULAN", "D_MURID", "STUDENT_MASTER", "SPP_TAGIHAN", "BUKU_KAS", "AUDIT_LOG"} <= set(sheets)


def test_every_table_has_a_model_with_exactly_its_stored_fields():
    for t in load_schema():
        names = {f.name for f in t.model_class()._meta.get_fields()}
        for f in t.fields:
            assert (f.name in names) == f.stored, (t.sheet, f.header)
            if f.text_field:
                assert f.text_field in names, (t.sheet, f.header)


def test_field_types_follow_the_schema():
    for t in load_schema():
        M = t.model_class()
        for f in t.stored_fields:
            field = M._meta.get_field(f.name)
            expected = models.CharField if (f.name == t.key and f.kind == "text") else KIND_FIELD[f.kind]
            assert isinstance(field, expected), (t.sheet, f.header, type(field))


def test_business_key_is_unique_per_branch():
    for t in load_schema():
        uniques = [tuple(c.fields) for c in t.model_class()._meta.constraints]
        assert (("branch", t.key) in uniques) == t.unique, t.sheet
    assert table("IMPORT_LOG").unique is False


def test_mixed_and_formula_columns():
    sm = table("STUDENT_MASTER").field_by_header
    assert sm["Harga SPP"].kind == "number" and sm["Harga SPP"].text_field
    assert sm["Join"].text_field
    assert sm["Status Sekarang"].stored is False
    assert table("SPP_TAGIHAN").field_by_header["Status Pembayaran"].stored is False
    assert table("SESI").field_by_header["Murid Hadir"].kind == "number"


def test_simulation_sheet_is_a_fixed_block():
    sim = table("SIMULASI_JADWAL")
    assert sim.skip_key_only and sim.stop_at_blank
    assert not any(t.stop_at_blank for t in load_schema() if t.sheet != "SIMULASI_JADWAL")
```

- [ ] **Step 3: Jalankan uji — harus gagal**

Run: `.venv/Scripts/python -m pytest importer/tests/test_schema_models.py`
Expected: FAIL (`LookupError: No installed app with label 'students'`).

- [ ] **Step 4: Generator model**

`tools/generate_models.py`:
```python
"""Tulis <app>/models_excel.py untuk setiap app dari importer/schema/excel_tables.json (file DIBANGKITKAN).
    .venv/Scripts/python tools/generate_models.py"""
import json
from collections import defaultdict
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent
SCHEMA = WEB / "importer" / "schema" / "excel_tables.json"
FIELD = {
    "text": 'models.TextField({v}, blank=True, default=""{x})',
    "number": "models.FloatField({v}, null=True, blank=True{x})",
    "date": "models.DateField({v}, null=True, blank=True{x})",
    "datetime": "models.DateTimeField({v}, null=True, blank=True{x})",
    "time": "models.TimeField({v}, null=True, blank=True{x})",
    "bool": "models.BooleanField({v}, null=True, blank=True{x})",
}
INDEXED = {"Student ID", "Parent ID", "Class ID", "Teacher ID", "Kode Kelas", "Periode", "Student ID (konversi)", "Lead ID"}


def field_line(f, is_key):
    v = repr(f["header"])
    if is_key and f["kind"] == "text":
        return f'    {f["name"]} = models.CharField({v}, max_length=200, db_index=True)'
    x = ", db_index=True" if (is_key or f["header"] in INDEXED) else ""
    return f'    {f["name"]} = ' + FIELD[f["kind"]].format(v=v, x=x)


def model_block(t):
    lines = [f'class {t["model"]}(ExcelRow):', f'    EXCEL_SHEET = {t["sheet"]!r}', f'    EXCEL_KEY = {t["key"]!r}', ""]
    for f in t["fields"]:
        if not f["stored"]:
            continue
        lines.append(field_line(f, f["name"] == t["key"]))
        if f["text_field"]:
            lines.append(f'    {f["text_field"]} = models.TextField({(f["header"] + " (teks asli)")!r}, blank=True, default="")')
    lines += ["", "    class Meta(ExcelRow.Meta):", f'        db_table = "x_{t["sheet"].lower()}"',
              f'        verbose_name = {t["sheet"]!r}', f'        verbose_name_plural = {t["sheet"]!r}']
    if t["unique"]:
        lines.append(f'        constraints = [models.UniqueConstraint(fields=["branch", {t["key"]!r}], name="uq_{t["sheet"].lower()}_key")]')
    return "\n".join(lines)


def main():
    data = json.loads(SCHEMA.read_text(encoding="utf-8"))
    by_app = defaultdict(list)
    for t in data["tables"]:
        by_app[t["app"]].append(t)
    for app, tables in by_app.items():
        head = ("# DIBANGKITKAN oleh tools/generate_models.py dari importer/schema/excel_tables.json - jangan diedit tangan.\n"
                "# Satu model per tabel Excel v4; kolom FORMULA tidak disimpan (dihitung oleh service).\n"
                "from django.db import models\n\nfrom core.models import ExcelRow\n\n"
                f"__all__ = {[t['model'] for t in tables]!r}\n\n\n")
        (WEB / app / "models_excel.py").write_text(head + "\n\n\n".join(model_block(t) for t in tables) + "\n", encoding="utf-8")
        print(app, [t["model"] for t in tables])


if __name__ == "__main__":
    main()
```

Buat app (untuk setiap `APP` dalam `masterdata students classes finance quality audit`):
```bash
for APP in masterdata students classes finance quality audit; do
  mkdir -p "$APP"
  : > "$APP/__init__.py"
  printf 'from .models_excel import *  # noqa: F401,F403  (tabel Excel v4 yang dibangkitkan)\n' > "$APP/models.py"
done
```
`masterdata/apps.py`:
```python
from django.apps import AppConfig


class MasterdataConfig(AppConfig):
    name = "masterdata"
    verbose_name = "Master data"
```
`students/apps.py`: sama dengan `name = "students"`, `verbose_name = "Murid"`, kelas `StudentsConfig`.
`classes/apps.py`: `name = "classes"`, `verbose_name = "Kelas"`, kelas `ClassesConfig`.
`finance/apps.py`: `name = "finance"`, `verbose_name = "Keuangan"`, kelas `FinanceConfig`.
`quality/apps.py`: `name = "quality"`, `verbose_name = "Kualitas data"`, kelas `QualityConfig`.
`audit/apps.py`: `name = "audit"`, `verbose_name = "Audit"`, kelas `AuditConfig`.

Run: `.venv/Scripts/python tools/generate_models.py`
Expected: enam baris, mis. `students ['StudentMaster', 'StudentIdMapping', 'StudentOff', ...]`.

Modify `spi_web/settings.py` — tambahkan ke akhir `INSTALLED_APPS`:
```python
    "masterdata",
    "students",
    "classes",
    "finance",
    "quality",
    "audit",
    "importer",
```

- [ ] **Step 5: Migrasi & jalankan uji**

Run:
```bash
.venv/Scripts/python manage.py makemigrations masterdata students classes finance quality audit
.venv/Scripts/python manage.py migrate
.venv/Scripts/python -m pytest
```
Expected: semua lulus.

- [ ] **Step 6: Commit**

```bash
git add tools importer masterdata students classes finance quality audit spi_web/settings.py
git commit -m "feat: skema tabel Excel v4 dan 34 model yang dibangkitkan" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Penomoran ID (IdBaru) dan jejak audit (CatatAudit)

**Files:**
- Create: `core/ids.py`, `core/audit.py`, `core/tests/test_ids_audit.py`

**Interfaces:**
- Consumes: `branches.models.Branch`, `students.StudentMaster` (`std`), `audit.AuditLog` (`lid`, `user`, `action`, `entity`, `eid`, `field`, `old`, `new`, `ts`, `by`).
- Produces:
  - `core.ids.next_id(model, field, prefix, digits, branch) -> str` (wajib di dalam `transaction.atomic()`)
  - `core.ids.next_row_no(model, branch) -> int`
  - `core.audit.actor_name(user) -> str`
  - `core.audit.log(*, branch, user, action, entity, entity_id, field="", old="", new="", detected_by="APLIKASI") -> AuditLog`

- [ ] **Step 1: Tulis uji yang gagal**

`core/tests/test_ids_audit.py`:
```python
import threading
import time

import pytest
from django.db import connection, transaction

from audit.models import AuditLog
from core import audit
from core.ids import next_id, next_row_no
from students.models import StudentMaster


@pytest.mark.django_db
def test_next_id_follows_the_largest_number_of_the_prefix(branch, other_branch):
    with transaction.atomic():
        assert next_id(StudentMaster, "std", "STD-", 6, branch) == "STD-000001"
    StudentMaster.objects.create(branch=branch, std="STD-000009", row_no=1)
    StudentMaster.objects.create(branch=branch, std="STD-00001X", row_no=2)       # bukan angka: diabaikan
    StudentMaster.objects.create(branch=branch, std="STD-0000000000123", row_no=3)  # >= 10 digit: diabaikan (seperti VBA)
    StudentMaster.objects.create(branch=other_branch, std="STD-000050", row_no=1)   # cabang lain: tidak dihitung
    with transaction.atomic():
        assert next_id(StudentMaster, "std", "STD-", 6, branch) == "STD-000010"


@pytest.mark.django_db
def test_next_id_refuses_to_run_outside_a_transaction(branch):
    with pytest.raises(RuntimeError):
        next_id(StudentMaster, "std", "STD-", 6, branch)


@pytest.mark.django_db
def test_next_row_no_appends_after_the_last_row(branch):
    assert next_row_no(StudentMaster, branch) == 1
    StudentMaster.objects.create(branch=branch, std="STD-000001", row_no=329)
    assert next_row_no(StudentMaster, branch) == 330


@pytest.mark.django_db(transaction=True)
def test_two_users_saving_at_once_get_different_ids(branch):
    barrier, results, errors = threading.Barrier(2), [], []

    def save_one():
        try:
            with transaction.atomic():
                barrier.wait(timeout=10)
                sid = next_id(StudentMaster, "std", "STD-", 6, branch)
                time.sleep(0.3)                                   # lebarkan jendela balapan
                StudentMaster.objects.create(branch=branch, std=sid, row_no=1)
                results.append(sid)
        except Exception as exc:                                  # noqa: BLE001 - dilaporkan oleh assert
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=save_one) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert errors == []
    assert sorted(results) == ["STD-000001", "STD-000002"]


@pytest.mark.django_db
def test_audit_log_numbers_rows_per_branch(branch, other_branch, make_user):
    user = make_user("admin@spi.test", full_name="Admin Uji")
    first = audit.log(branch=branch, user=user, action="CREATE", entity="STUDENT_MASTER", entity_id="STD-000001", new="Murid baru")
    second = audit.log(branch=branch, user=user, action="UPDATE", entity="STUDENT_MASTER", entity_id="STD-000001", field="Harga",
                       old=450000.0, new=500000.0)
    elsewhere = audit.log(branch=other_branch, user=None, action="CREATE", entity="CABANG", entity_id="SPI-AS")
    assert (first.lid, second.lid, elsewhere.lid) == ("LOG-000001", "LOG-000002", "LOG-000001")
    assert first.user == "Admin Uji" and first.by == "APLIKASI" and first.ts is not None
    assert (second.old, second.new) == ("450000", "500000")
    assert elsewhere.user == "sistem"
    assert AuditLog.objects.for_branch(branch).count() == 2
```

- [ ] **Step 2: Jalankan uji — harus gagal**

Run: `.venv/Scripts/python -m pytest core/tests/test_ids_audit.py`
Expected: FAIL (`ModuleNotFoundError: No module named 'core.ids'`).

- [ ] **Step 3: Implementasi**

`core/ids.py`:
```python
"""IdBaru (VBA Excel): nomor berikutnya setelah nomor tertinggi dengan awalan itu - nomor tidak pernah dipakai dua kali."""
from django.db import transaction
from django.db.models import Max

from branches.models import Branch


def next_id(model, field, prefix, digits, branch):
    """Harus dipanggil di dalam transaction.atomic(): baris cabang dikunci agar dua pengguna tidak mendapat nomor yang sama."""
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("next_id() harus dipanggil di dalam transaction.atomic()")
    list(Branch.objects.select_for_update().filter(pk=branch.pk).values_list("pk", flat=True))
    top = 0
    for value in model.objects.filter(branch=branch, **{f"{field}__startswith": prefix}).values_list(field, flat=True):
        rest = str(value)[len(prefix):]
        if rest.isdigit() and len(rest) < 10:
            top = max(top, int(rest))
    return f"{prefix}{top + 1:0{digits}d}"


def next_row_no(model, branch):
    return (model.objects.filter(branch=branch).aggregate(m=Max("row_no"))["m"] or 0) + 1
```

`core/audit.py`:
```python
"""CatatAudit (VBA Excel): satu baris AUDIT_LOG per perubahan - siapa, kapan, apa, nilai lama -> baru."""
import datetime

from django.db import transaction
from django.utils import timezone

from .ids import next_id, next_row_no


def actor_name(user):
    if user is None:
        return "sistem"
    return getattr(user, "full_name", "") or getattr(user, "email", "") or "sistem"


def _text(value):
    if value is None:
        return ""
    if isinstance(value, datetime.datetime):
        return timezone.localtime(value).strftime("%d %b %Y %H:%M") if timezone.is_aware(value) else value.strftime("%d %b %Y %H:%M")
    if isinstance(value, datetime.date):
        return value.strftime("%d %b %Y")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


@transaction.atomic
def log(*, branch, user, action, entity, entity_id, field="", old="", new="", detected_by="APLIKASI"):
    from audit.models import AuditLog

    return AuditLog.objects.create(
        branch=branch, row_no=next_row_no(AuditLog, branch), lid=next_id(AuditLog, "lid", "LOG-", 6, branch),
        user=actor_name(user), action=action, entity=entity, eid=str(entity_id), field=field,
        old=_text(old), new=_text(new), ts=timezone.now(), by=detected_by)
```

- [ ] **Step 4: Jalankan uji**

Run: `.venv/Scripts/python -m pytest core/tests/test_ids_audit.py`
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add core/ids.py core/audit.py core/tests/test_ids_audit.py
git commit -m "feat: penomoran ID (IdBaru) dengan kunci cabang dan jejak audit" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Kerangka aplikasi — cabang aktif, menu, beranda, pengguna & akses

**Files:**
- Create: `package.json`, `assets/app.css`, `assets/copy-vendor.mjs`, `static/img/spi-logo.png` (salinan logo), `static/css/app.css` (hasil build), `static/vendor/htmx.min.js`, `static/vendor/alpine.min.js`
- Create: `core/branch_context.py`, `core/decorators.py`, `core/nav.py`, `core/views.py`, `core/urls.py`
- Create: `templates/base.html`, `core/templates/core/home.html`, `core/templates/core/choose_branch.html`, `core/templates/core/no_access.html`, `core/templates/core/forbidden.html`, `core/templates/core/_icon.html`, `core/templates/core/_messages.html`
- Create: `accounts/forms.py`, `accounts/views_admin.py`, `accounts/urls.py`, `accounts/templates/accounts/users.html`
- Create: `core/tests/test_shell.py`, `accounts/tests/test_access_admin.py`
- Modify: `spi_web/settings.py` (MIDDLEWARE, context processor), `spi_web/urls.py`

**Interfaces:**
- Consumes: `Cap`, `caps_for`, `role_of`, `ROLE_LABELS` (Task 2); `core.audit.log` (Task 4); model Excel (Task 3).
- Produces:
  - `core.branch_context.SESSION_KEY = "spi_branch_id"`, `allowed_branches(user) -> QuerySet[Branch]`, `BranchContextMiddleware` (mengisi `request.branch`, `request.role`, `request.caps`), context processor `branch_context`
  - `core.decorators.require_cap(cap)` — login wajib, cabang aktif wajib, kemampuan wajib (403 bila tidak)
  - `core.nav.NAV`, `core.nav.nav_for(request)` — menu hanya berisi halaman yang ada dan boleh dibuka
  - URL: `core:home` (`/`), `core:switch_branch` (`/cabang-aktif/`), `accounts:logout` (`/akun/keluar/`), `accounts:users` (`/akun/pengguna/`), `accounts:revoke` (`/akun/pengguna/<id>/cabut/`)
  - template `base.html` (blok `title`, `content`), `core/_icon.html` (`name`), `core/_messages.html`

- [ ] **Step 1: Aset tampilan (Tailwind, HTMX, Alpine, logo)**

`package.json`:
```json
{
  "name": "spi-web-assets",
  "private": true,
  "scripts": {
    "build:css": "tailwindcss -i ./assets/app.css -o ./static/css/app.css --minify",
    "watch:css": "tailwindcss -i ./assets/app.css -o ./static/css/app.css --watch",
    "vendor": "node ./assets/copy-vendor.mjs"
  }
}
```

`assets/app.css`:
```css
@import "tailwindcss";
@source "../templates";
@source "../core/templates";
@source "../accounts/templates";
@source "../importer/templates";
@source "../branches/templates";

@theme {
  --color-brand-50: #eef4ff;
  --color-brand-100: #dce8ff;
  --color-brand-500: #176df8;
  --color-brand-600: #0f5fe0;
  --color-brand-700: #0b4bb3;
  --color-brand-900: #041a5a;
}

[x-cloak] { display: none !important; }

@layer components {
  .btn { @apply inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50 disabled:cursor-not-allowed disabled:opacity-50; }
  .btn-primary { @apply bg-brand-600 text-white shadow-sm hover:bg-brand-700; }
  .btn-secondary { @apply border border-slate-300 bg-white text-slate-700 hover:bg-slate-50; }
  .btn-danger { @apply bg-red-600 text-white hover:bg-red-700; }
  .card { @apply rounded-xl border border-slate-200 bg-white shadow-sm; }
  .badge { @apply inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold; }
  .form label { @apply mb-1 block text-sm font-medium text-slate-700; }
  .form input:not([type=checkbox]):not([type=radio]), .form select, .form textarea {
    @apply block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30;
  }
  .form .errorlist { @apply mt-1 text-sm text-red-600; }
  .form .helptext { @apply mt-1 block text-xs text-slate-500; }
}
```

`assets/copy-vendor.mjs`:
```js
import { copyFileSync, mkdirSync } from "node:fs";

mkdirSync("static/vendor", { recursive: true });
copyFileSync("node_modules/htmx.org/dist/htmx.min.js", "static/vendor/htmx.min.js");
copyFileSync("node_modules/alpinejs/dist/cdn.min.js", "static/vendor/alpine.min.js");
console.log("vendor: htmx, alpine disalin ke static/vendor");
```

Run:
```bash
npm install --save-dev @tailwindcss/cli tailwindcss htmx.org alpinejs
mkdir -p static/img
cp "/c/Users/SPI Workshop/Downloads/full app/SPI Logo 2025 blue transparent (2).png" static/img/spi-logo.png
npm run vendor
npm run build:css
```
Expected: `static/vendor/htmx.min.js`, `static/vendor/alpine.min.js`, `static/css/app.css` ada; `package.json` kini berisi `devDependencies`. (Ulangi `npm run build:css` setiap template baru ditambahkan — dilakukan di akhir Task 6, 9, 10.)

- [ ] **Step 2: Tulis uji yang gagal**

`core/tests/test_shell.py`:
```python
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
def test_teacher_has_no_branch_pages_yet(client, branch, make_user):
    client.force_login(make_user("guru@spi.test", role="TEACHER", branch=branch, teacher_name="Mr. Uji"))
    assert client.get("/").status_code == 403


@pytest.mark.django_db
def test_menu_shows_only_allowed_items(client, branch, make_user):
    client.force_login(make_user("admin@spi.test", role="BRANCH_ADMIN", branch=branch))
    assert "Pengguna &amp; Akses" in client.get("/").content.decode()
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    assert "Pengguna &amp; Akses" not in client.get("/").content.decode()
```

`accounts/tests/test_access_admin.py`:
```python
import pytest
from django.urls import reverse

from audit.models import AuditLog
from branches.models import Membership


@pytest.mark.django_db
def test_only_branch_admin_opens_the_users_page(client, branch, make_user):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    assert client.get(reverse("accounts:users")).status_code == 403


@pytest.mark.django_db
def test_branch_admin_grants_a_role_and_it_is_audited(client, branch, make_user):
    client.force_login(make_user("admin@spi.test", role="BRANCH_ADMIN", branch=branch))
    newbie = make_user("baru@spi.test")
    page = client.get(reverse("accounts:users")).content.decode()
    assert "baru@spi.test" in page                                     # daftar menunggu akses
    response = client.post(reverse("accounts:users"), {"email": "BARU@spi.test", "role": "FINANCE"})
    assert response.status_code == 302
    assert Membership.objects.get(user=newbie, branch=branch).role == "FINANCE"
    log = AuditLog.objects.for_branch(branch).get()
    assert (log.action, log.entity, log.eid, log.new) == ("ACCESS", "PENGGUNA", "baru@spi.test", "FINANCE")


@pytest.mark.django_db
def test_unverified_or_unknown_email_cannot_be_granted(client, branch, make_user):
    client.force_login(make_user("admin@spi.test", role="BRANCH_ADMIN", branch=branch))
    make_user("belum@spi.test", active=False)
    for email in ("belum@spi.test", "tidakada@spi.test"):
        response = client.post(reverse("accounts:users"), {"email": email, "role": "CSO"})
        assert response.status_code == 200 and "Tidak ada pengguna aktif" in response.content.decode()
    assert Membership.objects.filter(branch=branch).count() == 1


@pytest.mark.django_db
def test_teacher_role_needs_the_teacher_name(client, branch, make_user):
    client.force_login(make_user("admin@spi.test", role="BRANCH_ADMIN", branch=branch))
    make_user("guru@spi.test")
    response = client.post(reverse("accounts:users"), {"email": "guru@spi.test", "role": "TEACHER"})
    assert "Isi nama guru" in response.content.decode()


@pytest.mark.django_db
def test_revoking_a_membership_of_another_branch_is_not_found(client, branch, other_branch, make_user):
    client.force_login(make_user("admin@spi.test", role="BRANCH_ADMIN", branch=branch))
    foreign = Membership.objects.create(user=make_user("x@spi.test"), branch=other_branch, role="CSO")
    assert client.post(reverse("accounts:revoke", args=[foreign.pk])).status_code == 404
    assert Membership.objects.filter(pk=foreign.pk).exists()


@pytest.mark.django_db
def test_revoke_in_own_branch_removes_and_audits(client, branch, make_user):
    client.force_login(make_user("admin@spi.test", role="BRANCH_ADMIN", branch=branch))
    member = Membership.objects.create(user=make_user("cso@spi.test"), branch=branch, role="CSO")
    assert client.post(reverse("accounts:revoke", args=[member.pk])).status_code == 302
    assert not Membership.objects.filter(pk=member.pk).exists()
    assert AuditLog.objects.for_branch(branch).get().new == "(dicabut)"
```

- [ ] **Step 3: Jalankan uji — harus gagal**

Run: `.venv/Scripts/python -m pytest core/tests/test_shell.py accounts/tests/test_access_admin.py`
Expected: FAIL (`/` belum punya URL; `core.branch_context` belum ada).

- [ ] **Step 4: Cabang aktif, dekorator, menu**

`core/branch_context.py`:
```python
"""Cabang aktif per sesi: hanya cabang tempat pengguna punya peran (SUPER_ADMIN: semua)."""
from branches.models import Branch

from .capabilities import ROLE_LABELS, caps_for, role_of
from .nav import nav_for

SESSION_KEY = "spi_branch_id"


def allowed_branches(user):
    if not getattr(user, "is_authenticated", False):
        return Branch.objects.none()
    if user.is_super_admin:
        return Branch.objects.all()
    return Branch.objects.filter(memberships__user=user).distinct()


def _session_branch(allowed, session):
    try:
        pk = int(session.get(SESSION_KEY))
    except (TypeError, ValueError):
        return None
    return allowed.filter(pk=pk).first()


class BranchContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.branch, request.role, request.caps = None, None, frozenset()
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            allowed = allowed_branches(user)
            branch = _session_branch(allowed, request.session)
            if branch is None:
                request.session.pop(SESSION_KEY, None)
                if allowed.count() == 1:
                    branch = allowed.first()
                    request.session[SESSION_KEY] = branch.pk
            request.branch = branch
            request.role = role_of(user, branch)
            request.caps = caps_for(user, branch)
        return self.get_response(request)


def branch_context(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {"current_branch": getattr(request, "branch", None), "allowed_branches": list(allowed_branches(user)),
            "role": getattr(request, "role", None), "role_label": ROLE_LABELS.get(getattr(request, "role", None), ""),
            "caps": getattr(request, "caps", frozenset()), "nav": nav_for(request)}
```

`core/decorators.py`:
```python
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


def require_cap(cap):
    """Halaman cabang: login, cabang aktif, dan kemampuan `cap` untuk peran pengguna di cabang itu (dicek di server)."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(request, *args, **kwargs):
            if request.branch is None:
                return redirect("core:home")
            if cap not in request.caps:
                return render(request, "core/forbidden.html", status=403)
            return view(request, *args, **kwargs)
        return wrapped
    return decorator
```

`core/nav.py`:
```python
"""Menu samping: hanya halaman yang sudah ada (URL terdaftar) dan boleh dibuka peran pengguna di cabang aktif."""
from django.urls import NoReverseMatch, reverse

from .capabilities import Cap

NAV = (
    (None, (("Beranda", "core:home", Cap.VIEW, "home"),)),
    ("Admin", (("Impor Data", "importer:upload", Cap.BRANCH_ADMIN, "upload"),
               ("Pengguna & Akses", "accounts:users", Cap.BRANCH_ADMIN, "users"),
               ("Cabang", "branches:list", Cap.MANAGE_ALL, "building"))),
)


def nav_for(request):
    caps = getattr(request, "caps", frozenset())
    groups = []
    for label, items in NAV:
        shown = []
        for text, url_name, cap, icon in items:
            if cap not in caps:
                continue
            try:
                href = reverse(url_name)
            except NoReverseMatch:
                continue
            active = request.path == href if href == "/" else request.path.startswith(href)
            shown.append({"label": text, "href": href, "icon": icon, "active": active})
        if shown:
            groups.append({"label": label, "items": shown})
    return groups
```

- [ ] **Step 5: Beranda & pindah cabang**

`core/views.py`:
```python
from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from branches.models import Branch

from .branch_context import SESSION_KEY, allowed_branches
from .capabilities import Cap

COUNT_TABLES = (
    ("Murid", "students.StudentMaster"), ("Orang tua", "students.ParentMaster"), ("Riwayat bulanan", "students.DBulan"),
    ("Kejadian Off", "students.StudentOff"), ("Kelas", "classes.ClassMaster"), ("Anggota kelas", "classes.ClassMembers"),
    ("Slot jadwal", "classes.ClassSchedule"), ("Guru", "masterdata.TeacherMaster"), ("Program & level", "masterdata.ProgramMaster"),
    ("Baris buku kas", "finance.BukuKas"), ("Pengeluaran", "finance.BukuKasKeluar"), ("Periode", "finance.Periode"),
    ("Tagihan SPP", "finance.SppTagihan"), ("Issue data", "quality.IssueUnit"), ("Audit log", "audit.AuditLog"),
)


@login_required
def home(request):
    if request.branch is None:
        branches = allowed_branches(request.user)
        if not branches.exists():
            return render(request, "core/no_access.html")
        return render(request, "core/choose_branch.html", {"branches": branches})
    if Cap.VIEW not in request.caps:
        return render(request, "core/no_access.html", {"reason": "role"}, status=403)
    counts = [{"label": label, "count": apps.get_model(model).objects.for_branch(request.branch).count()} for label, model in COUNT_TABLES]
    return render(request, "core/home.html", {"counts": counts})


@login_required
@require_POST
def switch_branch(request):
    try:
        branch = allowed_branches(request.user).get(pk=int(request.POST.get("branch", "")))
    except (ValueError, TypeError, Branch.DoesNotExist):
        return render(request, "core/forbidden.html", status=403)
    request.session[SESSION_KEY] = branch.pk
    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}, request.is_secure()):
        return redirect(nxt)
    return redirect("core:home")
```

`core/urls.py`:
```python
from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    path("", views.home, name="home"),
    path("cabang-aktif/", views.switch_branch, name="switch_branch"),
]
```

- [ ] **Step 6: Pengguna & akses**

`accounts/forms.py`:
```python
from django import forms
from django.core.exceptions import ValidationError

from branches.models import Membership

from .models import User


class GrantAccessForm(forms.Form):
    email = forms.EmailField(label="Email pengguna")
    role = forms.ChoiceField(label="Peran", choices=Membership.ROLE_CHOICES)
    teacher_name = forms.CharField(label="Nama guru (untuk peran Teacher)", required=False, max_length=100,
                                   help_text="Nama seperti di jadwal & sesi, mis. Mr. Tryo")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is None:
            raise ValidationError("Tidak ada pengguna aktif (email terverifikasi) dengan email ini.")
        self.user = user
        return email

    def clean(self):
        data = super().clean()
        if data.get("role") == "TEACHER" and not data.get("teacher_name"):
            self.add_error("teacher_name", "Isi nama guru seperti di jadwal.")
        return data
```

`accounts/views_admin.py`:
```python
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from branches.models import Membership
from core import audit
from core.capabilities import Cap
from core.decorators import require_cap

from .forms import GrantAccessForm
from .models import User


@require_cap(Cap.BRANCH_ADMIN)
def users_view(request):
    branch = request.branch
    form = GrantAccessForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user, role = form.user, form.cleaned_data["role"]
        old = Membership.objects.filter(user=user, branch=branch).first()
        with transaction.atomic():
            Membership.objects.update_or_create(user=user, branch=branch, defaults={
                "role": role, "teacher_name": form.cleaned_data["teacher_name"], "created_by": request.user})
            audit.log(branch=branch, user=request.user, action="ACCESS", entity="PENGGUNA", entity_id=user.email,
                      field="Peran", old=old.role if old else "", new=role)
        messages.success(request, f"Akses {user.email} di {branch.name}: {role}.")
        return redirect("accounts:users")
    members = branch.memberships.select_related("user").order_by("user__full_name")
    pending = User.objects.filter(is_active=True, is_super_admin=False, memberships__isnull=True).order_by("date_joined")
    return render(request, "accounts/users.html", {"form": form, "members": members, "pending": pending})


@require_POST
@require_cap(Cap.BRANCH_ADMIN)
def revoke_view(request, membership_id):
    member = get_object_or_404(Membership.objects.select_related("user"), pk=membership_id, branch=request.branch)
    with transaction.atomic():
        audit.log(branch=request.branch, user=request.user, action="ACCESS", entity="PENGGUNA", entity_id=member.user.email,
                  field="Peran", old=member.role, new="(dicabut)")
        member.delete()
    messages.success(request, f"Akses {member.user.email} dicabut.")
    return redirect("accounts:users")
```

`accounts/urls.py`:
```python
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views_admin

app_name = "accounts"
urlpatterns = [
    path("keluar/", auth_views.LogoutView.as_view(), name="logout"),
    path("pengguna/", views_admin.users_view, name="users"),
    path("pengguna/<int:membership_id>/cabut/", views_admin.revoke_view, name="revoke"),
]
```

`spi_web/urls.py`:
```python
from django.urls import include, path

urlpatterns = [
    path("", include("core.urls")),
    path("akun/", include("accounts.urls")),
]
```

Modify `spi_web/settings.py`: tambahkan `"core.branch_context.BranchContextMiddleware",` sebagai baris terakhir `MIDDLEWARE`, dan `"core.branch_context.branch_context",` sebagai baris terakhir `context_processors`.

- [ ] **Step 7: Template**

`templates/base.html`:
```html
{% load static %}<!doctype html>
<html lang="id" class="h-full bg-slate-50">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}SPI Management{% endblock %}{% if current_branch %} · {{ current_branch.name }}{% endif %}</title>
  <link rel="icon" href="{% static 'img/spi-logo.png' %}">
  <link rel="stylesheet" href="{% static 'css/app.css' %}">
  <script src="{% static 'vendor/htmx.min.js' %}" defer></script>
  <script src="{% static 'vendor/alpine.min.js' %}" defer></script>
</head>
<body class="h-full text-slate-800" hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
<div x-data="{ open: false }" class="min-h-full">
  <div x-show="open" x-cloak class="fixed inset-0 z-20 bg-slate-900/40 lg:hidden" @click="open = false"></div>
  <aside class="fixed inset-y-0 left-0 z-30 w-64 -translate-x-full bg-brand-900 text-white transition-transform lg:translate-x-0"
         :class="open && 'translate-x-0'">
    <div class="flex h-16 items-center gap-3 border-b border-white/10 px-5">
      <img src="{% static 'img/spi-logo.png' %}" alt="SPI" class="h-8 w-8 rounded bg-white object-contain p-0.5">
      <div class="leading-tight"><p class="text-sm font-semibold">SPI Management</p>
        <p class="text-xs text-blue-200/80">{{ current_branch.name|default:"Pilih cabang" }}</p></div>
    </div>
    <nav class="space-y-6 px-3 py-4">
      {% for group in nav %}
        <div>
          {% if group.label %}<p class="px-3 pb-2 text-xs font-semibold uppercase tracking-wider text-blue-200/60">{{ group.label }}</p>{% endif %}
          <ul class="space-y-1">
            {% for item in group.items %}
              <li><a href="{{ item.href }}" class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm {% if item.active %}bg-white/15 font-semibold text-white{% else %}text-blue-100 hover:bg-white/10{% endif %}">
                {% include "core/_icon.html" with name=item.icon %}<span>{{ item.label }}</span></a></li>
            {% endfor %}
          </ul>
        </div>
      {% endfor %}
    </nav>
  </aside>
  <div class="lg:pl-64">
    <header class="sticky top-0 z-10 flex h-16 items-center gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur lg:px-8">
      <button type="button" class="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden" @click="open = true" aria-label="Buka menu">
        {% include "core/_icon.html" with name="menu" %}</button>
      {% if allowed_branches|length > 1 %}
        <form method="post" action="{% url 'core:switch_branch' %}">{% csrf_token %}
          <input type="hidden" name="next" value="{{ request.get_full_path }}">
          <select name="branch" onchange="this.form.submit()" aria-label="Cabang aktif"
                  class="rounded-lg border border-slate-300 bg-white py-1.5 pl-3 pr-8 text-sm font-semibold text-slate-800">
            {% if not current_branch %}<option value="">Pilih cabang…</option>{% endif %}
            {% for b in allowed_branches %}<option value="{{ b.pk }}" {% if current_branch and b.pk == current_branch.pk %}selected{% endif %}>{{ b.name }}</option>{% endfor %}
          </select>
        </form>
      {% elif current_branch %}
        <span class="text-sm font-semibold text-slate-800">{{ current_branch.name }}</span>
      {% endif %}
      <div class="ml-auto flex items-center gap-3">
        <div class="hidden text-right text-sm leading-tight sm:block">
          <p class="font-medium text-slate-800">{{ user.display_name }}</p>
          {% if role_label %}<p class="text-xs text-slate-500">{{ role_label }}</p>{% endif %}
        </div>
        <form method="post" action="{% url 'accounts:logout' %}">{% csrf_token %}<button class="btn btn-secondary">Keluar</button></form>
      </div>
    </header>
    <main class="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      {% include "core/_messages.html" %}
      {% block content %}{% endblock %}
    </main>
  </div>
</div>
</body>
</html>
```

`core/templates/core/_messages.html`:
```html
{% if messages %}<div class="mb-4 space-y-2">{% for m in messages %}
  <div class="rounded-lg border px-4 py-3 text-sm {% if m.tags == 'error' %}border-red-200 bg-red-50 text-red-800{% elif m.tags == 'success' %}border-emerald-200 bg-emerald-50 text-emerald-800{% elif m.tags == 'warning' %}border-amber-200 bg-amber-50 text-amber-900{% else %}border-blue-200 bg-blue-50 text-blue-800{% endif %}">{{ m }}</div>
{% endfor %}</div>{% endif %}
```

`core/templates/core/_icon.html`:
```html
<svg class="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
{% if name == "home" %}<path d="M3 11.5 12 4l9 7.5"/><path d="M5 10v10h14V10"/>
{% elif name == "upload" %}<path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M4 16v4h16v-4"/>
{% elif name == "users" %}<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7"/><path d="M18 14a6 6 0 0 1 3.5 6"/>
{% elif name == "building" %}<path d="M4 21V5l8-2v18"/><path d="M12 9h8v12"/><path d="M8 8h.01M8 12h.01M8 16h.01M16 13h.01M16 17h.01"/>
{% elif name == "menu" %}<path d="M4 6h16M4 12h16M4 18h16"/>
{% else %}<circle cx="12" cy="12" r="8"/>{% endif %}
</svg>
```

`core/templates/core/home.html`:
```html
{% extends "base.html" %}
{% block title %}Beranda{% endblock %}
{% block content %}
<div class="mb-6">
  <h1 class="text-2xl font-semibold text-slate-900">{{ current_branch.name }}</h1>
  <p class="text-sm text-slate-500">{{ current_branch.code }} · {{ current_branch.unit_id }} · {{ current_branch.city|default:"kota belum diisi" }} · status {{ current_branch.status }}</p>
</div>
<div class="card p-5">
  <h2 class="text-sm font-semibold uppercase tracking-wide text-slate-500">Isi data cabang</h2>
  <dl class="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
    {% for c in counts %}
      <div class="rounded-lg bg-slate-50 p-3"><dt class="text-xs text-slate-500">{{ c.label }}</dt>
        <dd class="mt-1 text-xl font-semibold text-slate-900">{{ c.count }}</dd></div>
    {% endfor %}
  </dl>
</div>
{% endblock %}
```

`core/templates/core/choose_branch.html`:
```html
{% extends "base.html" %}
{% block title %}Pilih cabang{% endblock %}
{% block content %}
<div class="mx-auto max-w-lg card p-6">
  <h1 class="text-lg font-semibold">Pilih cabang</h1>
  <p class="mt-1 text-sm text-slate-500">Anda punya akses ke beberapa cabang. Data setiap cabang terpisah.</p>
  <ul class="mt-4 space-y-2">{% for b in branches %}
    <li><form method="post" action="{% url 'core:switch_branch' %}">{% csrf_token %}<input type="hidden" name="branch" value="{{ b.pk }}">
      <button class="w-full rounded-lg border border-slate-200 px-4 py-3 text-left hover:border-brand-500 hover:bg-brand-50">
        <span class="font-semibold">{{ b.name }}</span> <span class="text-sm text-slate-500">{{ b.code }}</span></button></form></li>
  {% endfor %}</ul>
</div>
{% endblock %}
```

`core/templates/core/no_access.html`:
```html
{% extends "base.html" %}
{% block title %}Belum ada akses{% endblock %}
{% block content %}
<div class="mx-auto max-w-lg card p-6 text-center">
  {% if reason == "role" %}
    <h1 class="text-lg font-semibold">Belum ada halaman untuk peran Anda</h1>
    <p class="mt-2 text-sm text-slate-500">Peran Anda di {{ current_branch.name }} belum punya halaman di aplikasi ini.</p>
  {% else %}
    <h1 class="text-lg font-semibold">Akun Anda belum punya akses cabang</h1>
    <p class="mt-2 text-sm text-slate-500">Minta Branch Admin cabang Anda memberi peran untuk email <strong>{{ user.email }}</strong>.</p>
  {% endif %}
</div>
{% endblock %}
```

`core/templates/core/forbidden.html`:
```html
{% extends "base.html" %}
{% block title %}Tidak diizinkan{% endblock %}
{% block content %}
<div class="mx-auto max-w-lg card p-6 text-center">
  <h1 class="text-lg font-semibold">Tidak diizinkan</h1>
  <p class="mt-2 text-sm text-slate-500">Peran Anda di cabang ini tidak boleh membuka halaman atau menjalankan aksi ini.</p>
  <a href="{% url 'core:home' %}" class="btn btn-secondary mt-4">Kembali ke beranda</a>
</div>
{% endblock %}
```

`accounts/templates/accounts/users.html`:
```html
{% extends "base.html" %}
{% block title %}Pengguna & Akses{% endblock %}
{% block content %}
<h1 class="mb-6 text-2xl font-semibold text-slate-900">Pengguna & Akses <span class="text-base font-normal text-slate-500">· {{ current_branch.name }}</span></h1>
<div class="grid gap-6 lg:grid-cols-3">
  <div class="card overflow-hidden lg:col-span-2">
    <table class="min-w-full divide-y divide-slate-200 text-sm">
      <thead class="bg-slate-50 text-left text-xs font-semibold uppercase text-slate-500">
        <tr><th class="px-4 py-3">Nama</th><th class="px-4 py-3">Email</th><th class="px-4 py-3">Peran</th><th class="px-4 py-3"></th></tr></thead>
      <tbody class="divide-y divide-slate-100">
        {% for m in members %}
          <tr><td class="px-4 py-3 font-medium">{{ m.user.display_name }}</td><td class="px-4 py-3 text-slate-600">{{ m.user.email }}</td>
            <td class="px-4 py-3"><span class="badge bg-brand-50 text-brand-700">{{ m.get_role_display }}</span>{% if m.teacher_name %} <span class="text-xs text-slate-500">({{ m.teacher_name }})</span>{% endif %}</td>
            <td class="px-4 py-3 text-right"><form method="post" action="{% url 'accounts:revoke' m.pk %}" onsubmit="return confirm('Cabut akses {{ m.user.email|escapejs }}?')">{% csrf_token %}<button class="text-sm font-semibold text-red-600 hover:underline">Cabut</button></form></td></tr>
        {% empty %}<tr><td colspan="4" class="px-4 py-6 text-center text-slate-500">Belum ada pengguna di cabang ini.</td></tr>{% endfor %}
      </tbody>
    </table>
  </div>
  <div class="space-y-6">
    <form method="post" class="card form space-y-4 p-5">{% csrf_token %}
      <h2 class="font-semibold">Beri / ubah akses</h2>
      {% for field in form %}<div>{{ field.label_tag }}{{ field }}{% if field.help_text %}<span class="helptext">{{ field.help_text }}</span>{% endif %}{{ field.errors }}</div>{% endfor %}
      <button class="btn btn-primary w-full">Simpan akses</button>
    </form>
    <div class="card p-5">
      <h2 class="font-semibold">Menunggu akses</h2>
      <p class="mt-1 text-xs text-slate-500">Email sudah terverifikasi, belum punya peran di cabang mana pun.</p>
      <ul class="mt-3 space-y-1 text-sm">{% for u in pending %}<li>{{ u.display_name }} · <span class="text-slate-600">{{ u.email }}</span></li>{% empty %}<li class="text-slate-500">Tidak ada.</li>{% endfor %}</ul>
    </div>
  </div>
</div>
{% endblock %}
```

Run: `npm run build:css`

- [ ] **Step 8: Jalankan semua uji**

Run: `.venv/Scripts/python -m pytest`
Expected: semua lulus (termasuk 7 uji kerangka + 6 uji akses).

- [ ] **Step 9: Commit**

```bash
git add package.json package-lock.json assets static templates core accounts spi_web
git commit -m "feat: kerangka aplikasi - cabang aktif, menu per peran, beranda, pengguna & akses" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Autentikasi — masuk, daftar, verifikasi email, lupa & reset password

**Files:**
- Create: `accounts/tokens.py`, `accounts/ratelimit.py`, `accounts/emails.py`, `accounts/views.py`
- Modify: `accounts/forms.py` (tambah `LoginForm`, `SignupForm`, `ResendForm`), `accounts/urls.py`
- Create: `templates/base_auth.html`, `accounts/templates/accounts/{login,signup,signup_done,verify_failed,resend,password_reset_form,password_reset_done,password_reset_confirm,password_reset_complete}.html`
- Create: `accounts/templates/accounts/email/{verify_subject.txt,verify_body.txt,registered_subject.txt,registered_body.txt,reset_subject.txt,reset_body.txt}`
- Create: `accounts/tests/test_auth.py`

**Interfaces:**
- Consumes: `accounts.User` (Task 1), settings `LOGIN_MAX_ATTEMPTS`, `LOGIN_BLOCK_SECONDS`, `PASSWORD_RESET_TIMEOUT`.
- Produces: `accounts.tokens.email_verification_token`; `accounts.ratelimit.is_blocked(email, ip)`, `register_failure(email, ip)`, `reset(email, ip)`; `accounts.emails.send_verification(request, user)`, `send_already_registered(request, user)`; URL `accounts:login` (`/akun/masuk/`), `accounts:signup`, `accounts:signup_done`, `accounts:verify`, `accounts:resend`, `accounts:password_reset`, `accounts:password_reset_done`, `accounts:password_reset_confirm`, `accounts:password_reset_complete`.

- [ ] **Step 1: Tulis uji yang gagal**

`accounts/tests/test_auth.py`:
```python
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
    return re.search(r"https?://[^/\s]+(/\S*" + re.escape(part) + r"\S*)", message.body).group(1)


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
```

- [ ] **Step 2: Jalankan uji — harus gagal**

Run: `.venv/Scripts/python -m pytest accounts/tests/test_auth.py`
Expected: FAIL (`NoReverseMatch: 'signup' is not a valid view function or pattern name`).

- [ ] **Step 3: Token, pembatas percobaan, email**

`accounts/tokens.py`:
```python
from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Tautan verifikasi email: berlaku PASSWORD_RESET_TIMEOUT, hanya sekali (berubah begitu akun aktif)."""
    key_salt = "spi_web.accounts.EmailVerificationTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.email}{user.is_active}{user.email_verified_at}{timestamp}"


email_verification_token = EmailVerificationTokenGenerator()
```

`accounts/ratelimit.py`:
```python
"""Pembatas percobaan masuk: LOGIN_MAX_ATTEMPTS kegagalan per (email, IP) dalam LOGIN_BLOCK_SECONDS -> diblokir."""
from django.conf import settings
from django.core.cache import cache


def _key(email, ip):
    return f"login-fail:{(email or '').strip().lower()}:{ip}"


def is_blocked(email, ip):
    return cache.get(_key(email, ip), 0) >= settings.LOGIN_MAX_ATTEMPTS


def register_failure(email, ip):
    key = _key(email, ip)
    cache.add(key, 0, settings.LOGIN_BLOCK_SECONDS)
    cache.incr(key)


def reset(email, ip):
    cache.delete(_key(email, ip))
```

`accounts/emails.py`:
```python
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import email_verification_token


def _send(template, user, context):
    subject = render_to_string(f"accounts/email/{template}_subject.txt", context).strip()
    body = render_to_string(f"accounts/email/{template}_body.txt", context)
    send_mail(subject, body, None, [user.email])


def send_verification(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    url = request.build_absolute_uri(reverse("accounts:verify", args=[uid, email_verification_token.make_token(user)]))
    _send("verify", user, {"user": user, "url": url})


def send_already_registered(request, user):
    _send("registered", user, {"user": user, "login_url": request.build_absolute_uri(reverse("accounts:login")),
                                "reset_url": request.build_absolute_uri(reverse("accounts:password_reset"))})
```

- [ ] **Step 4: Form & view**

Tambahkan ke `accounts/forms.py` (di bawah import yang ada; tambah `from django.contrib.auth.password_validation import validate_password`):
```python
class LoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Password", strip=False, widget=forms.PasswordInput)


class SignupForm(forms.Form):
    full_name = forms.CharField(label="Nama lengkap", max_length=150)
    email = forms.EmailField(label="Email")
    password1 = forms.CharField(label="Password", strip=False, widget=forms.PasswordInput,
                                help_text="Minimal 10 karakter, tidak mirip nama / email, tidak umum.")
    password2 = forms.CharField(label="Ulangi password", strip=False, widget=forms.PasswordInput)

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean(self):
        data = super().clean()
        p1, p2 = data.get("password1"), data.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Password tidak sama.")
        elif p1:
            try:
                validate_password(p1, user=User(email=data.get("email", ""), full_name=data.get("full_name", "")))
            except ValidationError as exc:
                self.add_error("password1", exc)
        return data


class ResendForm(forms.Form):
    email = forms.EmailField(label="Email")
```

`accounts/views.py`:
```python
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode

from . import ratelimit
from .emails import send_already_registered, send_verification
from .forms import LoginForm, ResendForm, SignupForm
from .models import User
from .tokens import email_verification_token


def _client_ip(request):
    return request.META.get("REMOTE_ADDR", "")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:home")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email, password, ip = form.cleaned_data["email"].lower(), form.cleaned_data["password"], _client_ip(request)
        if ratelimit.is_blocked(email, ip):
            form.add_error(None, "Terlalu banyak percobaan gagal. Coba lagi dalam 15 menit.")
        else:
            user = authenticate(request, username=email, password=password)
            if user is None:
                ratelimit.register_failure(email, ip)
                pending = User.objects.filter(email__iexact=email, is_active=False, email_verified_at__isnull=True).first()
                if pending is not None and pending.check_password(password):
                    form.add_error(None, "Email belum diverifikasi. Buka tautan di email Anda atau kirim ulang tautan verifikasi.")
                else:
                    form.add_error(None, "Email atau password salah.")
            else:
                ratelimit.reset(email, ip)
                login(request, user)
                nxt = request.GET.get("next", "")
                if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}, request.is_secure()):
                    return redirect(nxt)
                return redirect("core:home")
    return render(request, "accounts/login.html", {"form": form})


def signup_view(request):
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        existing = User.objects.filter(email__iexact=email).first()
        if existing is not None:
            send_already_registered(request, existing)
        else:
            user = User.objects.create_user(email, form.cleaned_data["password1"], full_name=form.cleaned_data["full_name"])
            send_verification(request, user)
        return redirect("accounts:signup_done")
    return render(request, "accounts/signup.html", {"form": form})


def signup_done_view(request):
    return render(request, "accounts/signup_done.html")


def verify_view(request, uidb64, token):
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None
    if user is not None and not user.is_active and email_verification_token.check_token(user, token):
        user.is_active = True
        user.email_verified_at = timezone.now()
        user.save(update_fields=["is_active", "email_verified_at"])
        messages.success(request, "Email terverifikasi. Silakan masuk. Akses cabang diberikan oleh Branch Admin.")
        return redirect("accounts:login")
    return render(request, "accounts/verify_failed.html", status=400)


def resend_view(request):
    form = ResendForm(request.POST or None)
    sent = False
    if request.method == "POST" and form.is_valid():
        user = User.objects.filter(email__iexact=form.cleaned_data["email"], is_active=False, email_verified_at__isnull=True).first()
        if user is not None:
            send_verification(request, user)
        sent = True                                   # jawaban sama untuk email apa pun
    return render(request, "accounts/resend.html", {"form": form, "sent": sent})
```

`accounts/urls.py` (ganti seluruhnya):
```python
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views, views_admin

app_name = "accounts"
urlpatterns = [
    path("masuk/", views.login_view, name="login"),
    path("keluar/", auth_views.LogoutView.as_view(), name="logout"),
    path("daftar/", views.signup_view, name="signup"),
    path("daftar/terkirim/", views.signup_done_view, name="signup_done"),
    path("verifikasi/kirim-ulang/", views.resend_view, name="resend"),
    path("verifikasi/<uidb64>/<token>/", views.verify_view, name="verify"),
    path("lupa-password/", auth_views.PasswordResetView.as_view(
        template_name="accounts/password_reset_form.html", email_template_name="accounts/email/reset_body.txt",
        subject_template_name="accounts/email/reset_subject.txt", success_url=reverse_lazy("accounts:password_reset_done")),
        name="password_reset"),
    path("lupa-password/terkirim/", auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
         name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/password_reset_confirm.html", success_url=reverse_lazy("accounts:password_reset_complete")),
        name="password_reset_confirm"),
    path("reset/selesai/", auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"),
         name="password_reset_complete"),
    path("pengguna/", views_admin.users_view, name="users"),
    path("pengguna/<int:membership_id>/cabut/", views_admin.revoke_view, name="revoke"),
]
```

- [ ] **Step 5: Template autentikasi & email**

`templates/base_auth.html`:
```html
{% load static %}<!doctype html>
<html lang="id" class="h-full bg-slate-50">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Masuk{% endblock %} · SPI Management</title>
  <link rel="icon" href="{% static 'img/spi-logo.png' %}">
  <link rel="stylesheet" href="{% static 'css/app.css' %}">
</head>
<body class="flex min-h-full items-center justify-center bg-gradient-to-br from-brand-900 via-brand-700 to-brand-500 px-4 py-10 text-slate-800">
  <div class="w-full max-w-md">
    <div class="mb-6 flex items-center justify-center gap-3 text-white">
      <img src="{% static 'img/spi-logo.png' %}" alt="SPI" class="h-12 w-12 rounded-lg bg-white object-contain p-1">
      <div><p class="text-lg font-semibold leading-tight">SPI Management</p><p class="text-sm text-blue-100">Murid · Kelas · SPP · Akademik</p></div>
    </div>
    <div class="card p-6 sm:p-8">
      {% include "core/_messages.html" %}
      {% block content %}{% endblock %}
    </div>
  </div>
</body>
</html>
```

`accounts/templates/accounts/login.html`:
```html
{% extends "base_auth.html" %}
{% block title %}Masuk{% endblock %}
{% block content %}
<h1 class="text-xl font-semibold text-slate-900">Masuk</h1>
<form method="post" class="form mt-6 space-y-4">{% csrf_token %}
  {% if form.non_field_errors %}<div class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{{ form.non_field_errors|join:" " }}</div>{% endif %}
  {% for field in form %}<div>{{ field.label_tag }}{{ field }}{{ field.errors }}</div>{% endfor %}
  <button class="btn btn-primary w-full">Masuk</button>
</form>
<div class="mt-6 flex flex-wrap justify-between gap-2 text-sm">
  <a href="{% url 'accounts:password_reset' %}" class="font-semibold text-brand-600 hover:underline">Lupa password?</a>
  <a href="{% url 'accounts:signup' %}" class="font-semibold text-brand-600 hover:underline">Daftar akun</a>
  <a href="{% url 'accounts:resend' %}" class="w-full text-slate-500 hover:underline">Kirim ulang tautan verifikasi email</a>
</div>
{% endblock %}
```

`accounts/templates/accounts/signup.html`:
```html
{% extends "base_auth.html" %}
{% block title %}Daftar{% endblock %}
{% block content %}
<h1 class="text-xl font-semibold text-slate-900">Daftar akun</h1>
<p class="mt-1 text-sm text-slate-500">Setelah email diverifikasi, Branch Admin cabang Anda memberi peran & akses.</p>
<form method="post" class="form mt-6 space-y-4">{% csrf_token %}
  {% for field in form %}<div>{{ field.label_tag }}{{ field }}{% if field.help_text %}<span class="helptext">{{ field.help_text }}</span>{% endif %}{{ field.errors }}</div>{% endfor %}
  <button class="btn btn-primary w-full">Daftar</button>
</form>
<p class="mt-6 text-sm"><a href="{% url 'accounts:login' %}" class="font-semibold text-brand-600 hover:underline">Sudah punya akun? Masuk</a></p>
{% endblock %}
```

`accounts/templates/accounts/signup_done.html`:
```html
{% extends "base_auth.html" %}
{% block title %}Cek email{% endblock %}
{% block content %}
<h1 class="text-xl font-semibold text-slate-900">Cek email Anda</h1>
<p class="mt-2 text-sm text-slate-600">Kami mengirim tautan ke alamat email yang Anda isi. Buka tautan itu dalam 24 jam untuk mengaktifkan akun.</p>
<a href="{% url 'accounts:login' %}" class="btn btn-secondary mt-6">Kembali ke halaman masuk</a>
{% endblock %}
```

`accounts/templates/accounts/verify_failed.html`:
```html
{% extends "base_auth.html" %}
{% block title %}Tautan tidak berlaku{% endblock %}
{% block content %}
<h1 class="text-xl font-semibold text-slate-900">Tautan tidak berlaku</h1>
<p class="mt-2 text-sm text-slate-600">Tautan verifikasi sudah dipakai, sudah kedaluwarsa, atau tidak lengkap.</p>
<a href="{% url 'accounts:resend' %}" class="btn btn-primary mt-6">Kirim tautan baru</a>
{% endblock %}
```

`accounts/templates/accounts/resend.html`:
```html
{% extends "base_auth.html" %}
{% block title %}Kirim ulang verifikasi{% endblock %}
{% block content %}
<h1 class="text-xl font-semibold text-slate-900">Kirim ulang tautan verifikasi</h1>
{% if sent %}
  <p class="mt-2 text-sm text-slate-600">Bila email itu terdaftar dan belum diverifikasi, tautan baru sudah dikirim.</p>
  <a href="{% url 'accounts:login' %}" class="btn btn-secondary mt-6">Kembali ke halaman masuk</a>
{% else %}
  <form method="post" class="form mt-6 space-y-4">{% csrf_token %}
    {% for field in form %}<div>{{ field.label_tag }}{{ field }}{{ field.errors }}</div>{% endfor %}
    <button class="btn btn-primary w-full">Kirim</button>
  </form>
{% endif %}
{% endblock %}
```

`accounts/templates/accounts/password_reset_form.html`:
```html
{% extends "base_auth.html" %}
{% block title %}Lupa password{% endblock %}
{% block content %}
<h1 class="text-xl font-semibold text-slate-900">Lupa password</h1>
<p class="mt-1 text-sm text-slate-500">Masukkan email akun Anda; kami kirim tautan untuk membuat password baru.</p>
<form method="post" class="form mt-6 space-y-4">{% csrf_token %}
  {% for field in form %}<div>{{ field.label_tag }}{{ field }}{{ field.errors }}</div>{% endfor %}
  <button class="btn btn-primary w-full">Kirim tautan</button>
</form>
{% endblock %}
```

`accounts/templates/accounts/password_reset_done.html`:
```html
{% extends "base_auth.html" %}
{% block title %}Cek email{% endblock %}
{% block content %}
<h1 class="text-xl font-semibold text-slate-900">Cek email Anda</h1>
<p class="mt-2 text-sm text-slate-600">Bila email itu terdaftar dan aktif, tautan untuk membuat password baru sudah dikirim.</p>
<a href="{% url 'accounts:login' %}" class="btn btn-secondary mt-6">Kembali ke halaman masuk</a>
{% endblock %}
```

`accounts/templates/accounts/password_reset_confirm.html`:
```html
{% extends "base_auth.html" %}
{% block title %}Password baru{% endblock %}
{% block content %}
{% if validlink %}
  <h1 class="text-xl font-semibold text-slate-900">Buat password baru</h1>
  <form method="post" class="form mt-6 space-y-4">{% csrf_token %}
    {% for field in form %}<div>{{ field.label_tag }}{{ field }}{{ field.errors }}</div>{% endfor %}
    <button class="btn btn-primary w-full">Simpan password</button>
  </form>
{% else %}
  <h1 class="text-xl font-semibold text-slate-900">Tautan tidak berlaku</h1>
  <p class="mt-2 text-sm text-slate-600">Tautan sudah dipakai atau kedaluwarsa.</p>
  <a href="{% url 'accounts:password_reset' %}" class="btn btn-primary mt-6">Minta tautan baru</a>
{% endif %}
{% endblock %}
```

`accounts/templates/accounts/password_reset_complete.html`:
```html
{% extends "base_auth.html" %}
{% block title %}Password diganti{% endblock %}
{% block content %}
<h1 class="text-xl font-semibold text-slate-900">Password sudah diganti</h1>
<a href="{% url 'accounts:login' %}" class="btn btn-primary mt-6">Masuk</a>
{% endblock %}
```

`accounts/templates/accounts/email/verify_subject.txt`:
```
Verifikasi email akun SPI Management
```

`accounts/templates/accounts/email/verify_body.txt`:
```
Halo {{ user.full_name }},

Buka tautan berikut untuk memverifikasi email akun SPI Management Anda (berlaku 24 jam, sekali pakai):

{{ url }}

Setelah terverifikasi, Branch Admin cabang Anda akan memberi peran dan akses.
Bila Anda tidak mendaftar, abaikan email ini.
```

`accounts/templates/accounts/email/registered_subject.txt`:
```
Akun SPI Management Anda sudah ada
```

`accounts/templates/accounts/email/registered_body.txt`:
```
Halo {{ user.full_name }},

Ada pendaftaran baru memakai email ini, tetapi akun dengan email ini sudah terdaftar - tidak ada akun kedua yang dibuat.

Masuk: {{ login_url }}
Lupa password: {{ reset_url }}
```

`accounts/templates/accounts/email/reset_subject.txt`:
```
Buat password baru SPI Management
```

`accounts/templates/accounts/email/reset_body.txt`:
```
Halo {{ user.full_name }},

Buka tautan berikut untuk membuat password baru (sekali pakai):

{{ protocol }}://{{ domain }}{% url 'accounts:password_reset_confirm' uidb64=uid token=token %}

Bila Anda tidak memintanya, abaikan email ini; password lama tetap berlaku.
```

Run: `npm run build:css`

- [ ] **Step 6: Jalankan uji**

Run: `.venv/Scripts/python -m pytest`
Expected: semua lulus (termasuk 11 uji autentikasi).

- [ ] **Step 7: Commit**

```bash
git add accounts templates static/css/app.css
git commit -m "feat: daftar, verifikasi email, masuk dengan pembatas percobaan, lupa & reset password" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Inti importer — membaca workbook, mengubah nilai, memvalidasi

**Files:**
- Create: `importer/convert.py`, `importer/reader.py`, `importer/validate.py`
- Create: `importer/tests/factories.py`, `importer/tests/test_convert.py`, `importer/tests/test_reader_validate.py`

**Interfaces:**
- Consumes: `importer.schema` (Task 3), `branches.models.Branch.unit_id` (Task 2).
- Produces:
  - `importer.convert.ConvertError`; `convert(field: FieldSpec, raw) -> dict` (nama field → nilai; plus `<nama>_text` untuk kolom campur)
  - `importer.reader.WorkbookError`; `SheetRow(row: int, values: dict)`; `WorkbookData(tables, missing_headers, settings)` dengan `unit`, `setting(key)`; `read_workbook(path) -> WorkbookData`; konstanta `SETTINGS_SHEET = "SETTINGS"`
    - `settings` = list dict `{"key", "param", "value", "note", "row", "is_formula"}`
  - `importer.validate.Issue(level, table, row, field, message)` + `as_dict()`; `REFERENCE_RULES`; `validate(data, branch=None) -> list[Issue]`
  - `importer.tests.factories.build_workbook(path, rows=None, settings=None, drop_sheets=(), rename_headers=None) -> path`

- [ ] **Step 1: Pembuat workbook uji & uji yang gagal**

`importer/tests/factories.py`:
```python
"""Workbook SPI v4 minimal untuk uji: setiap sheet skema dengan baris judulnya; isi = {sheet: [{judul kolom: nilai}]}."""
import openpyxl

from importer.reader import SETTINGS_HEADER_ROW, SETTINGS_SHEET
from importer.schema import load_schema


def build_workbook(path, rows=None, settings=None, drop_sheets=(), rename_headers=None):
    rows, rename_headers = rows or {}, rename_headers or {}
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for spec in load_schema():
        if spec.sheet in drop_sheets:
            continue
        ws = wb.create_sheet(spec.sheet)
        for j, f in enumerate(spec.fields, 1):
            ws.cell(row=spec.header_row, column=j, value=rename_headers.get((spec.sheet, f.header), f.header))
        for i, record in enumerate(rows.get(spec.sheet, [])):
            for j, f in enumerate(spec.fields, 1):
                if f.header in record:
                    ws.cell(row=spec.data_row + i, column=j, value=record[f.header])
    ws = wb.create_sheet(SETTINGS_SHEET)
    for j, h in enumerate(("Parameter", "Nilai", "Keterangan", "Kunci"), 1):
        ws.cell(row=SETTINGS_HEADER_ROW, column=j, value=h)
    for i, (key, value) in enumerate((settings if settings is not None else {"unit": "UNIT-JKT"}).items()):
        r = SETTINGS_HEADER_ROW + 1 + i
        ws.cell(row=r, column=1, value=key)
        ws.cell(row=r, column=2, value=value)
        ws.cell(row=r, column=4, value=key)
    wb.save(path)
    return path
```

`importer/tests/test_convert.py`:
```python
import datetime

import pytest

from importer.convert import ConvertError, convert
from importer.schema import table

SM = table("STUDENT_MASTER").field_by_header


def test_text_keeps_the_value_and_whole_numbers_lose_the_decimal():
    assert convert(SM["Nama Murid"], "Abygail Greysel Chu") == {"nama": "Abygail Greysel Chu"}
    assert convert(SM["Nama Murid"], None) == {"nama": ""}
    assert convert(table("CLASS_MASTER").field_by_header["Kode Kelas"], 12.0)["code"] == "12"


def test_mixed_number_column_keeps_text_separately():
    assert convert(SM["Harga SPP"], 670000) == {"harga": 670000.0, "harga_text": ""}
    assert convert(SM["Harga SPP"], "Rp 500.000 (promo)") == {"harga": None, "harga_text": "Rp 500.000 (promo)"}


def test_mixed_date_column():
    assert convert(SM["Join"], datetime.datetime(2025, 12, 3)) == {"join": datetime.date(2025, 12, 3), "join_text": ""}
    assert convert(SM["Join"], "Agustus 2024") == {"join": None, "join_text": "Agustus 2024"}


def test_text_in_a_pure_number_column_is_an_error():
    with pytest.raises(ConvertError):
        convert(table("SPP_TAGIHAN").field_by_header["Harga SPP"], "lima ratus ribu")


def test_datetime_gets_the_jakarta_timezone():
    ts = convert(table("AUDIT_LOG").field_by_header["Timestamp"], datetime.datetime(2026, 9, 30, 8, 53))["ts"]
    assert ts.utcoffset() == datetime.timedelta(hours=7)


def test_time_from_a_day_fraction():
    mulai = table("SESI").field_by_header["Mulai"]
    assert convert(mulai, 0.375) == {"mulai": datetime.time(9, 0)}
    assert convert(mulai, datetime.time(15, 30)) == {"mulai": datetime.time(15, 30)}
```

`importer/tests/test_reader_validate.py`:
```python
import datetime

import pytest

from branches.models import Branch
from importer.reader import WorkbookError, read_workbook
from importer.tests.factories import build_workbook
from importer.validate import validate

STUDENTS = [
    {"Student ID": "STD-000001", "Nama Murid": "Ani", "Parent ID": "PAR-00001", "Harga SPP": 450000, "Tanggal Lahir": datetime.datetime(2016, 5, 10)},
    {"Student ID": "STD-000002", "Nama Murid": "Budi", "Parent ID": "PAR-00009", "Harga SPP": "gratis"},
]
PARENTS = [{"Parent ID": "PAR-00001", "Nama Orang Tua": "Ibu Ani"}]


def errors(issues):
    return [i for i in issues if i.level == "error"]


def test_valid_workbook_reads_rows_by_header(tmp_path):
    path = build_workbook(tmp_path / "ok.xlsx", {"STUDENT_MASTER": STUDENTS, "PARENT_MASTER": PARENTS})
    data = read_workbook(path)
    assert [r.values["std"] for r in data.tables["STUDENT_MASTER"]] == ["STD-000001", "STD-000002"]
    assert data.tables["STUDENT_MASTER"][0].row == 6
    assert data.unit == "UNIT-JKT"
    issues = validate(data, Branch(code="SPI-JKT", name="SPI Jakarta"))
    assert errors(issues) == []
    assert [i.message for i in issues if i.level == "warning"] == ["'PAR-00009' tidak ada di PARENT_MASTER (Parent ID)."]


def test_file_that_is_not_excel_is_refused(tmp_path):
    path = tmp_path / "catatan.xlsx"
    path.write_text("bukan excel", encoding="utf-8")
    with pytest.raises(WorkbookError, match="bukan workbook Excel"):
        read_workbook(path)


def test_workbook_without_v4_sheets_is_refused(tmp_path):
    path = build_workbook(tmp_path / "v3.xlsx", drop_sheets=("SPP_TAGIHAN", "SESI"))
    with pytest.raises(WorkbookError, match="Bukan workbook SPI v4"):
        read_workbook(path)


def test_missing_column_is_an_error(tmp_path):
    path = build_workbook(tmp_path / "x.xlsx", rename_headers={("STUDENT_MASTER", "Nama Murid"): "Nama"})
    issues = validate(read_workbook(path))
    assert any(i.level == "error" and i.field == "Nama Murid" for i in issues)


def test_duplicate_ids_and_bad_values_are_errors(tmp_path):
    rows = {"STUDENT_MASTER": [STUDENTS[0], dict(STUDENTS[0])], "PARENT_MASTER": PARENTS,
            "SPP_TAGIHAN": [{"Tagihan ID": "TAG-202610-STD-000001", "Student ID": "STD-000001", "Harga SPP": "banyak"}]}
    messages = [i.message for i in errors(validate(read_workbook(build_workbook(tmp_path / "x.xlsx", rows))))]
    assert any("ID ganda 'STD-000001'" in m for m in messages)
    assert any("bukan angka" in m for m in messages)


def test_bill_for_unknown_student_is_an_error(tmp_path):
    rows = {"SPP_TAGIHAN": [{"Tagihan ID": "TAG-202610-STD-000404", "Student ID": "STD-000404", "Harga SPP": 450000}]}
    issues = errors(validate(read_workbook(build_workbook(tmp_path / "x.xlsx", rows))))
    assert [(i.table, i.field) for i in issues] == [("SPP_TAGIHAN", "Student ID")]


def test_twin_students_are_a_warning(tmp_path):
    twin = dict(STUDENTS[0], **{"Student ID": "STD-000003"})
    issues = validate(read_workbook(build_workbook(tmp_path / "x.xlsx", {"STUDENT_MASTER": [STUDENTS[0], twin], "PARENT_MASTER": PARENTS})))
    assert any(i.level == "warning" and "tanggal lahir sama" in i.message for i in issues)


def test_workbook_of_another_branch_is_an_error(tmp_path):
    data = read_workbook(build_workbook(tmp_path / "x.xlsx", settings={"unit": "UNIT-JKT"}))
    issues = errors(validate(data, Branch(code="SPI-AS", name="SPI Alam Sutera")))
    assert issues and "bukan UNIT-AS" in issues[0].message
    data = read_workbook(build_workbook(tmp_path / "y.xlsx", settings={"branch_id": "SPI-AS", "unit": "UNIT-AS"}))
    assert any("milik cabang SPI-AS" in i.message for i in errors(validate(data, Branch(code="SPI-JKT", name="SPI Jakarta"))))


def test_simulation_block_keeps_filled_rows_and_ends_at_the_first_blank_row(tmp_path):
    rows = {"SIMULASI_JADWAL": [{"No Simulasi": "SIM-01"}, {"No Simulasi": "SIM-02", "Murid": "Ani", "Hari": "SENIN"}, {},
                                {"No Simulasi": "Jam", "Murid": "Guru", "Jam Mulai": "Guru ▸"}]}   # tampilan JADWAL RESMI
    data = read_workbook(build_workbook(tmp_path / "x.xlsx", rows))
    assert [(r.row, r.values["no"], r.values["murid"]) for r in data.tables["SIMULASI_JADWAL"]] == [(7, "SIM-02", "Ani")]
    assert errors(validate(data)) == []
```

- [ ] **Step 2: Jalankan uji — harus gagal**

Run: `.venv/Scripts/python -m pytest importer/tests/test_convert.py importer/tests/test_reader_validate.py`
Expected: FAIL (`ModuleNotFoundError: No module named 'importer.convert'`).

- [ ] **Step 3: Konversi nilai sel**

`importer/convert.py`:
```python
"""Nilai sel Excel -> nilai field. Tidak ada nilai yang ditebak: teks di kolom angka/tanggal hanya diterima bila kolom itu 'campur'
(disimpan di <nama>_text, kolom bertipe kosong - sama seperti ISNUMBER / ISTEXT di Excel)."""
import datetime
from zoneinfo import ZoneInfo

from django.conf import settings


class ConvertError(ValueError):
    pass


def _tz():
    return ZoneInfo(settings.TIME_ZONE)


def _as_text(raw):
    if isinstance(raw, bool):
        return "TRUE" if raw else "FALSE"
    if isinstance(raw, float) and raw.is_integer():
        return str(int(raw))
    if isinstance(raw, datetime.datetime):
        return raw.isoformat(sep=" ")
    return str(raw)


def _typed(kind, raw):
    if kind == "number":
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ConvertError(f"bukan angka: {raw!r}")
        return float(raw)
    if kind == "date":
        if isinstance(raw, datetime.datetime):
            return raw.date()
        if isinstance(raw, datetime.date):
            return raw
        raise ConvertError(f"bukan tanggal: {raw!r}")
    if kind == "datetime":
        if isinstance(raw, datetime.datetime):
            value = raw
        elif isinstance(raw, datetime.date):
            value = datetime.datetime(raw.year, raw.month, raw.day)
        else:
            raise ConvertError(f"bukan tanggal & jam: {raw!r}")
        return value if value.tzinfo else value.replace(tzinfo=_tz())
    if kind == "time":
        if isinstance(raw, datetime.datetime):
            return raw.time()
        if isinstance(raw, datetime.time):
            return raw
        if isinstance(raw, (int, float)) and not isinstance(raw, bool) and 0 <= raw < 1:
            seconds = round(raw * 86400)
            return datetime.time(seconds // 3600, seconds % 3600 // 60, seconds % 60)
        raise ConvertError(f"bukan jam: {raw!r}")
    if kind == "bool":
        if isinstance(raw, bool):
            return raw
        raise ConvertError(f"bukan TRUE/FALSE: {raw!r}")
    raise ConvertError(f"jenis kolom tidak dikenal: {kind}")


def convert(field, raw):
    out = {field.text_field: ""} if field.text_field else {}
    if raw is None or raw == "":
        out[field.name] = "" if field.kind == "text" else None
        return out
    if field.kind == "text":
        out[field.name] = _as_text(raw)
        return out
    try:
        out[field.name] = _typed(field.kind, raw)
    except ConvertError:
        if field.text_field and isinstance(raw, str):
            out[field.name] = None
            out[field.text_field] = raw
            return out
        raise
    return out
```

- [ ] **Step 4: Pembaca workbook**

`importer/reader.py`:
```python
"""Membaca workbook SPI v4 lewat judul kolom (sama dengan pipeline). Hanya kolom tersimpan yang dibaca; nilai rumus diabaikan."""
import zipfile
from dataclasses import dataclass, field

import openpyxl
from openpyxl.utils.exceptions import InvalidFileException

from .schema import load_schema

SETTINGS_SHEET = "SETTINGS"
SETTINGS_HEADER_ROW = 5


class WorkbookError(Exception):
    pass


@dataclass
class SheetRow:
    row: int
    values: dict


@dataclass
class WorkbookData:
    tables: dict = field(default_factory=dict)
    missing_headers: dict = field(default_factory=dict)
    settings: list = field(default_factory=list)

    def setting(self, key):
        return next((s for s in self.settings if s["key"] == key), None)

    @property
    def unit(self):
        s = self.setting("unit")
        return str(s["value"]).strip() if s and s["value"] not in (None, "") else None


def _open(path, data_only):
    try:
        return openpyxl.load_workbook(path, read_only=True, data_only=data_only)
    except (InvalidFileException, zipfile.BadZipFile, KeyError, OSError, ValueError) as exc:
        raise WorkbookError("File bukan workbook Excel (.xlsx / .xlsm) yang bisa dibaca.") from exc


def _headers(ws, row):
    cells = next(ws.iter_rows(min_row=row, max_row=row, values_only=True), ())
    return {str(h).strip(): i for i, h in enumerate(cells) if h not in (None, "")}


def _read_table(ws, spec, data):
    hdr = _headers(ws, spec.header_row)
    cols, missing = {}, []
    for f in spec.stored_fields:
        i = hdr.get(f.header)
        if i is None:
            i = next((hdr[a] for a in f.aliases if a in hdr), None)
        if i is None:
            missing.append(f.header)
        else:
            cols[f.name] = i
    if missing:
        data.missing_headers[spec.sheet] = missing
    rows = []
    key_i = cols.get(spec.key)
    if key_i is not None:
        for r, cells in enumerate(ws.iter_rows(min_row=spec.data_row, values_only=True), spec.data_row):
            key = cells[key_i] if key_i < len(cells) else None
            if key in (None, ""):
                if spec.stop_at_blank:
                    break                          # akhir blok (SIMULASI_JADWAL: di bawahnya tampilan JADWAL RESMI, bukan data)
                continue
            values = {name: (cells[i] if i < len(cells) else None) for name, i in cols.items()}
            if spec.skip_key_only and all(v in (None, "") for n, v in values.items() if n != spec.key):
                continue
            rows.append(SheetRow(r, values))
    data.tables[spec.sheet] = rows


def _read_settings(ws_values, ws_formulas, data):
    hdr = _headers(ws_values, SETTINGS_HEADER_ROW)
    need = ("Parameter", "Nilai", "Keterangan", "Kunci")
    if any(h not in hdr for h in need):
        data.missing_headers[SETTINGS_SHEET] = [h for h in need if h not in hdr]
        return
    formula_rows = set()
    for r, cells in enumerate(ws_formulas.iter_rows(min_row=SETTINGS_HEADER_ROW + 1, values_only=True), SETTINGS_HEADER_ROW + 1):
        v = cells[hdr["Nilai"]] if hdr["Nilai"] < len(cells) else None
        if isinstance(v, str) and v.startswith("="):
            formula_rows.add(r)
    for r, cells in enumerate(ws_values.iter_rows(min_row=SETTINGS_HEADER_ROW + 1, values_only=True), SETTINGS_HEADER_ROW + 1):
        get = lambda h: cells[hdr[h]] if hdr[h] < len(cells) else None   # noqa: E731
        if get("Kunci") in (None, ""):
            continue
        data.settings.append({"key": str(get("Kunci")), "param": get("Parameter") or "", "value": get("Nilai"),
                              "note": get("Keterangan") or "", "row": r, "is_formula": r in formula_rows})


def read_workbook(path):
    wb = _open(path, data_only=True)
    try:
        names = set(wb.sheetnames)
        missing = [s for s in [t.sheet for t in load_schema()] + [SETTINGS_SHEET] if s not in names]
        if missing:
            shown = ", ".join(missing[:5]) + (f" dan {len(missing) - 5} lainnya" if len(missing) > 5 else "")
            raise WorkbookError(f"Bukan workbook SPI v4: sheet {shown} tidak ada.")
        data = WorkbookData()
        for spec in load_schema():
            _read_table(wb[spec.sheet], spec, data)
        wbf = _open(path, data_only=False)
        try:
            _read_settings(wb[SETTINGS_SHEET], wbf[SETTINGS_SHEET], data)
        finally:
            wbf.close()
        return data
    finally:
        wb.close()
```

- [ ] **Step 5: Validasi**

`importer/validate.py`:
```python
"""Pemeriksaan sebelum impor: kolom wajib, tipe nilai, ID ganda, rujukan, murid kembar, dan unit cabang."""
from dataclasses import asdict, dataclass

from .convert import ConvertError, convert
from .schema import load_schema, table


@dataclass
class Issue:
    level: str
    table: str
    row: int | None
    field: str
    message: str

    def as_dict(self):
        return asdict(self)


# (tabel, kolom, tabel tujuan, kolom tujuan, tingkat): nilai yang terisi harus ada di tabel tujuan
REFERENCE_RULES = (
    ("STATUS_EVENT", "Student ID", "STUDENT_MASTER", "Student ID", "error"),
    ("SPP_TAGIHAN", "Student ID", "STUDENT_MASTER", "Student ID", "error"),
    ("BUKTI_BAYAR", "Student ID", "STUDENT_MASTER", "Student ID", "error"),
    ("ACADEMIC_RECORD", "Student ID", "STUDENT_MASTER", "Student ID", "error"),
    ("DOKUMEN", "Student ID", "STUDENT_MASTER", "Student ID", "error"),
    ("FOLLOW_UP", "Student ID", "STUDENT_MASTER", "Student ID", "error"),
    ("FOLLOW_UP", "Lead ID", "LEAD", "Lead ID", "error"),
    ("LEAD", "Student ID (konversi)", "STUDENT_MASTER", "Student ID", "warning"),
    ("STUDENT_MASTER", "Parent ID", "PARENT_MASTER", "Parent ID", "warning"),
    ("STUDENT_OFF", "Student ID", "STUDENT_MASTER", "Student ID", "warning"),
    ("CLASS_MEMBERS", "Student ID", "STUDENT_MASTER", "Student ID", "warning"),
    ("SESI", "Slot Jadwal", "CLASS_SCHEDULE", "Schedule ID", "warning"),
    ("D_BULAN", "Student ID", "STUDENT_MASTER", "Student ID", "warning"),
)


def _values(data, sheet, name):
    return {str(r.values.get(name)) for r in data.tables.get(sheet, []) if r.values.get(name) not in (None, "")}


def validate(data, branch=None):
    issues = []
    for sheet, headers in data.missing_headers.items():
        issues += [Issue("error", sheet, None, h, f"Kolom '{h}' tidak ada di sheet {sheet}.") for h in headers]
    for spec in load_schema():
        seen = {}
        for r in data.tables.get(spec.sheet, []):
            for f in spec.stored_fields:
                if f.name in r.values:
                    try:
                        convert(f, r.values[f.name])
                    except ConvertError as exc:
                        issues.append(Issue("error", spec.sheet, r.row, f.header, str(exc)))
            key = r.values.get(spec.key)
            if spec.unique:
                if key in seen:
                    issues.append(Issue("error", spec.sheet, r.row, spec.field_by_name[spec.key].header,
                                        f"ID ganda '{key}' (juga di baris {seen[key]})."))
                else:
                    seen[key] = r.row
    for sheet, header, target, target_header, level in REFERENCE_RULES:
        f = table(sheet).field_by_header[header]
        known = _values(data, target, table(target).field_by_header[target_header].name)
        for r in data.tables.get(sheet, []):
            v = r.values.get(f.name)
            if v not in (None, "") and str(v) not in known:
                issues.append(Issue(level, sheet, r.row, header, f"'{v}' tidak ada di {target} ({target_header})."))
    issues += _twin_students(data)
    if branch is not None:
        issues += _branch_check(data, branch)
    return issues


def _twin_students(data):
    spec = table("STUDENT_MASTER")
    name_f, birth_f = spec.field_by_header["Nama Murid"], spec.field_by_header["Tanggal Lahir"]
    seen, out = {}, []
    for r in data.tables.get("STUDENT_MASTER", []):
        name, birth = r.values.get(name_f.name), r.values.get(birth_f.name)
        if name in (None, "") or birth in (None, ""):
            continue
        key = (str(name).strip().lower(), str(birth)[:10])
        if key in seen:
            out.append(Issue("warning", "STUDENT_MASTER", r.row, "Nama Murid",
                             f"Nama & tanggal lahir sama dengan baris {seen[key]} - pastikan bukan murid yang sama."))
        else:
            seen[key] = r.row
    return out


def _branch_check(data, branch):
    out = []
    code = data.setting("branch_id")
    if code and code["value"] and str(code["value"]).strip().upper() != branch.code.upper():
        out.append(Issue("error", "SETTINGS", code["row"], "Branch ID",
                         f"Workbook ini milik cabang {code['value']}, bukan {branch.code}. Data cabang lain tidak boleh diimpor."))
    unit = data.unit
    if not unit:
        out.append(Issue("warning", "SETTINGS", None, "Unit", f"Unit workbook tidak tercatat - pastikan workbook ini milik {branch.name}."))
    elif unit != branch.unit_id:
        out.append(Issue("error", "SETTINGS", None, "Unit",
                         f"Workbook ini milik unit {unit}, bukan {branch.unit_id} ({branch.name}). Data cabang lain tidak boleh diimpor."))
    return out
```

- [ ] **Step 6: Jalankan uji**

Run: `.venv/Scripts/python -m pytest importer`
Expected: semua lulus (6 uji konversi + 9 uji baca/validasi + uji skema).

- [ ] **Step 7: Commit**

```bash
git add importer
git commit -m "feat: importer - baca workbook v4 lewat judul kolom, konversi nilai, validasi" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Menyimpan impor — transaksi, riwayat audit, perintah, uji dengan workbook asli

**Files:**
- Modify: `importer/models.py` (ImportRun)
- Create: `importer/commit.py`, `importer/services.py`, `importer/management/__init__.py`, `importer/management/commands/__init__.py`, `importer/management/commands/import_workbook.py`
- Create: `importer/tests/test_commit.py`, `importer/tests/test_services.py`, `importer/tests/test_real_workbooks.py`

**Interfaces:**
- Consumes: `read_workbook`, `validate`, `convert` (Task 7); `core.audit.log`, `core.ids.next_id`, `next_row_no` (Task 4); `BranchSetting.split_value` (Task 2); `audit.AuditLog` (`lid`, `ts`, …), `audit.ImportLog` (`batch`, `date`, `file`, `path`, `sha`, `sheets`, `rows`, `excluded`, `ver`, `notes`).
- Produces:
  - `importer.commit.ImportBlocked`; `LOG_TABLES`; `IDENTITY_KEYS`; `NOT_STORED_KEYS`; `STORED_FORMULA_KEYS`; `stored_settings(settings) -> list[dict]`; `branch_has_data(branch) -> bool`; `commit_workbook(data, branch, user, *, replace, file_name, sha256, source_path="", note="") -> dict[str, int]`
  - `importer.models.ImportRun` (`branch`, `file`, `original_name`, `sha256`, `status` PREVIEW/COMMITTED/FAILED, `report`, `created_by`, `created_at`, `committed_by`, `committed_at`)
  - `importer.services.sha256_of(path) -> str`; `existing_counts(branch) -> dict[str, int]`; `build_report(path, branch) -> dict`; `create_run(uploaded_file, branch, user) -> ImportRun`; `commit_run(run, user, *, replace) -> dict[str, int]`; `grouped_counts(report) -> list[dict]`
  - perintah `python manage.py import_workbook <path> --branch SPI-JKT [--create --name ... --city ... --status ...] [--commit] [--replace]`

Aturan simpan (sama dengan pipeline Excel, spesifikasi §7.2):
- Semua tabel Excel kecuali riwayat: isi cabang diganti seluruhnya oleh isi workbook; `row_no` = nomor baris di sheet (urutan sama dengan Excel).
- Riwayat `AUDIT_LOG` dan `IMPORT_LOG` tidak pernah dihapus atau diubah. Baris workbook yang isinya sudah tersimpan dilewati (impor ulang tidak menggandakan). Log ID Excel dipakai apa adanya; bila ID itu sudah dipakai catatan web lain, baris workbook mendapat Log ID berikutnya dan jumlahnya dicatat di IMPORT_LOG.
- SETTINGS (`v2_build_sheets.py` `SET_ROWS`): 8 baris identitas → field `Branch` (perubahan dicatat di AUDIT_LOG); `branch_id` dicek validasi, `unit` dihitung dari Branch ID; baris rumus (periode, hari_ini, bulan_ini; di workbook cabang juga nota_kop, nota_awalan, mulai_v4) dihitung web → tidak disimpan, kecuali `ambang` (rumus `=ambang` hanya menunjuk sel isian CEK_SPP!B3); baris lain → `BranchSetting`.
- Batch impor web mengikuti pola batch cabang Excel: `IMP-<Branch ID tanpa SPI->-<yyyymmdd>-<NN>` (mis. `IMP-AS-20261001-01`).

- [ ] **Step 1: Tulis uji yang gagal**

`importer/tests/test_commit.py`:
```python
import datetime
import re

import pytest

from audit.models import AuditLog, ImportLog
from branches.models import BranchSetting
from core import audit
from importer.commit import ImportBlocked, branch_has_data, commit_workbook
from importer.reader import read_workbook
from importer.tests.factories import build_workbook
from students.models import StudentMaster

ROWS = {
    "STUDENT_MASTER": [{"Student ID": "STD-000001", "Nama Murid": "Ani", "Harga SPP": 450000, "Join": datetime.datetime(2025, 1, 6)},
                       {"Student ID": "STD-000002", "Nama Murid": "Budi", "Harga SPP": "gratis", "Join": "Agustus 2024"}],
    "AUDIT_LOG": [{"Log ID": "LOG-000001", "Action": "CREATE", "Entity": "WORKBOOK", "Detected By": "SYSTEM",
                   "Timestamp": datetime.datetime(2026, 9, 30, 8, 53)}],
}
SETTINGS = {"unit": "UNIT-JKT", "off_lama": 3, "nota_kop": "SPI Jakarta", "mulai_v4": datetime.datetime(2026, 10, 1),
            "versi": "v2.0-fase1", "hari_ini": "=TODAY()"}


@pytest.fixture
def data(tmp_path):
    return read_workbook(build_workbook(tmp_path / "jkt.xlsx", ROWS, SETTINGS))


def commit(data, branch, replace=False):
    return commit_workbook(data, branch, None, replace=replace, file_name="jkt.xlsx", sha256="abc")


@pytest.mark.django_db
def test_commit_stores_rows_in_sheet_order_with_mixed_values(data, branch, make_user):
    counts = commit_workbook(data, branch, make_user("admin@spi.test"), replace=False, file_name="jkt.xlsx", sha256="abc")
    assert counts["STUDENT_MASTER"] == 2 and counts["AUDIT_LOG"] == 1
    ani, budi = StudentMaster.objects.for_branch(branch).order_by("row_no")
    assert (ani.row_no, ani.harga, ani.join) == (6, 450000.0, datetime.date(2025, 1, 6))
    assert (budi.harga, budi.harga_text, budi.join, budi.join_text) == (None, "gratis", None, "Agustus 2024")


@pytest.mark.django_db
def test_commit_keeps_settings_except_identity_and_formulas_and_logs_the_import(data, branch):
    commit(data, branch)
    keys = set(BranchSetting.objects.filter(branch=branch).values_list("key", flat=True))
    assert keys == {"off_lama", "nota_kop", "mulai_v4", "versi"}       # 'unit' dari Branch ID; 'hari_ini' rumus
    assert BranchSetting.objects.get(branch=branch, key="mulai_v4").value == datetime.date(2026, 10, 1)
    log = ImportLog.objects.for_branch(branch).get()
    assert re.fullmatch(r"IMP-JKT-\d{8}-01", log.batch) and log.sha == "abc" and log.file == "jkt.xlsx"
    imported, ours = AuditLog.objects.for_branch(branch).order_by("row_no")
    assert (imported.lid, imported.by, ours.lid, ours.action, ours.eid) == ("LOG-000001", "SYSTEM", "LOG-000002", "IMPORT", "jkt.xlsx")


@pytest.mark.django_db
def test_second_import_needs_replace_and_never_duplicates(data, branch):
    commit(data, branch)
    assert branch_has_data(branch)
    with pytest.raises(ImportBlocked):
        commit(data, branch)
    commit(data, branch, replace=True)
    assert StudentMaster.objects.for_branch(branch).count() == 2
    assert list(AuditLog.objects.for_branch(branch).order_by("row_no").values_list("lid", "action")) == [
        ("LOG-000001", "CREATE"), ("LOG-000002", "IMPORT"), ("LOG-000003", "IMPORT")]
    assert [b[-3:] for b in ImportLog.objects.for_branch(branch).order_by("row_no").values_list("batch", flat=True)] == ["-01", "-02"]


@pytest.mark.django_db
def test_audit_history_written_by_the_web_is_kept_and_never_renumbered(data, branch):
    audit.log(branch=branch, user=None, action="GRANT", entity="PENGGUNA", entity_id="cso@spi.test", new="CSO")
    assert not branch_has_data(branch)                                # riwayat saja bukan data cabang
    commit(data, branch)
    commit(data, branch, replace=True)
    assert list(AuditLog.objects.for_branch(branch).order_by("row_no").values_list("lid", "action")) == [
        ("LOG-000001", "GRANT"), ("LOG-000002", "CREATE"), ("LOG-000003", "IMPORT"), ("LOG-000004", "IMPORT")]
    assert "1 baris AUDIT_LOG" in ImportLog.objects.for_branch(branch).order_by("row_no").first().notes


@pytest.mark.django_db
def test_import_does_not_touch_other_branches(data, branch, other_branch):
    StudentMaster.objects.create(branch=other_branch, std="STD-000001", nama="Murid AS", row_no=6)
    commit(data, branch)
    assert StudentMaster.objects.for_branch(other_branch).get().nama == "Murid AS"


@pytest.mark.django_db
def test_identity_rows_update_the_branch_and_are_audited(tmp_path, other_branch):
    settings = {"branch_id": "SPI-AS", "branch_name": "SPI Alam Sutera", "branch_city": "Tangerang", "branch_status": "ACTIVE",
                "branch_open": None, "unit": "UNIT-AS"}
    data = read_workbook(build_workbook(tmp_path / "as.xlsx", {}, settings))
    other_branch.city, other_branch.status = "", "NEW_BRANCH"
    other_branch.save()
    commit_workbook(data, other_branch, None, replace=False, file_name="as.xlsx", sha256="x")
    other_branch.refresh_from_db()
    assert (other_branch.city, other_branch.status, other_branch.opening_date) == ("Tangerang", "ACTIVE", None)
    assert not BranchSetting.objects.filter(branch=other_branch).exists()
    changes = AuditLog.objects.for_branch(other_branch).filter(action="UPDATE").order_by("row_no")
    assert [(c.entity, c.field, c.old, c.new) for c in changes] == [("CABANG", "Kota", "", "Tangerang"),
                                                                   ("CABANG", "Status cabang", "NEW_BRANCH", "ACTIVE")]
```

`importer/tests/test_services.py`:
```python
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command

from branches.models import Branch
from importer.commit import ImportBlocked
from importer.services import commit_run, create_run, grouped_counts
from importer.tests.factories import build_workbook
from students.models import StudentMaster

STUDENTS = {"STUDENT_MASTER": [{"Student ID": "STD-000001", "Nama Murid": "Ani"}]}


def upload(tmp_path, name="jkt.xlsx", rows=STUDENTS, settings=None):
    path = build_workbook(tmp_path / name, rows, settings)
    return SimpleUploadedFile(name, path.read_bytes())


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.mark.django_db
def test_preview_stores_nothing_and_commit_saves_once(tmp_path, branch, make_user):
    user = make_user("admin@spi.test")
    run = create_run(upload(tmp_path), branch, user)
    assert run.status == "PREVIEW" and run.report["ok"] and run.report["counts"]["STUDENT_MASTER"] == 1
    assert len(run.sha256) == 64 and not StudentMaster.objects.exists()
    students = next(g for g in grouped_counts(run.report) if g["label"] == "Murid")
    assert {"sheet": "STUDENT_MASTER", "new": 1, "existing": 0, "saved": None} in students["tables"]
    assert commit_run(run, user, replace=False)["STUDENT_MASTER"] == 1
    run.refresh_from_db()
    assert run.status == "COMMITTED" and run.committed_by == user
    with pytest.raises(ImportBlocked, match="sudah diproses"):
        commit_run(run, user, replace=True)
    assert StudentMaster.objects.count() == 1


@pytest.mark.django_db
def test_workbook_with_errors_or_of_another_branch_cannot_be_committed(tmp_path, branch, make_user):
    user = make_user("admin@spi.test")
    run = create_run(upload(tmp_path, settings={"unit": "UNIT-AS"}), branch, user)
    assert not run.report["ok"] and run.report["errors"] == 1
    with pytest.raises(ImportBlocked):
        commit_run(run, user, replace=False)
    broken = SimpleUploadedFile("rusak.xlsx", b"bukan excel")
    run = create_run(broken, branch, user)
    assert not run.report["ok"] and "bukan workbook Excel" in run.report["fatal"]
    assert not StudentMaster.objects.exists()


@pytest.mark.django_db
def test_command_previews_by_default_and_can_create_the_branch(tmp_path):
    settings = {"branch_id": "SPI-AS", "branch_name": "SPI Alam Sutera", "branch_city": "Tangerang", "unit": "UNIT-AS"}
    path = build_workbook(tmp_path / "as.xlsx", STUDENTS, settings)
    with pytest.raises(CommandError, match="--create"):
        call_command("import_workbook", str(path), "--branch", "SPI-AS")
    call_command("import_workbook", str(path), "--branch", "SPI-AS", "--create")
    assert not Branch.objects.exists()                               # pratinjau: cabang pun tidak disimpan
    call_command("import_workbook", str(path), "--branch", "spi-as", "--create", "--commit")
    branch = Branch.objects.get(code="SPI-AS")
    assert (branch.name, branch.city) == ("SPI Alam Sutera", "Tangerang")
    assert StudentMaster.objects.for_branch(branch).count() == 1
    with pytest.raises(CommandError, match="sudah berisi data"):
        call_command("import_workbook", str(path), "--branch", "SPI-AS", "--commit")
```

`importer/tests/test_real_workbooks.py`:
```python
"""Workbook asli di ..\\APP (hanya dibaca). Jalankan: .venv/Scripts/python -m pytest -m slow importer/tests/test_real_workbooks.py"""
import pytest
from django.conf import settings

from branches.models import Branch, BranchSetting
from importer.commit import commit_workbook
from importer.convert import convert
from importer.reader import WorkbookError, read_workbook
from importer.schema import load_schema
from importer.validate import validate

pytestmark = pytest.mark.slow
JKT = settings.SPI_EXCEL_DIR / "SPI_STUDENT-SPP_APP_2026_09_v4.xlsm"
AS = settings.SPI_EXCEL_DIR / "SPI_ALAM_SUTERA_v4.xlsm"
V3 = settings.SPI_EXCEL_DIR / "SPI_STUDENT-SPP_APP_2026_09_v3.xlsm"
JKT_COUNTS = {
    "STUDENT_MASTER": 324, "STUDENT_ID_MAPPING": 1448, "STUDENT_OFF": 152, "OFF_REASON_MASTER": 86, "CLASS_MASTER": 227,
    "CLASS_MEMBERS": 449, "CLASS_SCHEDULE": 116, "TEACHER_MASTER": 25, "PROGRAM_MASTER": 16, "PARTNER_MASTER": 126,
    "ROOM_MASTER": 8, "UNIT_MASTER": 11, "ISSUE_UNIT": 618, "BUKU_KAS": 3898, "PEMBAYAR": 172, "NOTA_LOG": 0, "SIMULASI_JADWAL": 0,
    "PERIODE": 33, "STATUS_EVENT": 0, "PARENT_MASTER": 172, "SPP_TAGIHAN": 0, "BUKTI_BAYAR": 0, "SESI": 0, "TARIF_FEE": 40,
    "FOLLOW_UP": 1, "ACADEMIC_RECORD": 0, "LEAD": 0, "DOKUMEN": 0, "BUKU_KAS_KELUAR": 1398, "IMPORT_LOG": 228,
    "SOURCE_REFERENCE": 18, "AUDIT_LOG": 13, "D_BULAN": 5488, "D_MURID": 324,
}


@pytest.fixture(scope="module")
def jkt_data():
    return read_workbook(JKT)


@pytest.mark.django_db
def test_jakarta_imports_without_errors_and_every_cell_is_kept(jkt_data):
    branch = Branch.objects.create(code="SPI-JKT", name="SPI Jakarta", city="Jakarta", status="ACTIVE")
    assert [i for i in validate(jkt_data, branch) if i.level == "error"] == []
    counts = commit_workbook(jkt_data, branch, None, replace=False, file_name=JKT.name, sha256="-")
    assert counts == JKT_COUNTS
    for spec in load_schema():
        rows = {o.row_no: o for o in spec.model_class().objects.for_branch(branch)}
        for r in jkt_data.tables[spec.sheet]:
            obj = rows[r.row]
            for f in spec.stored_fields:
                for name, expected in convert(f, r.values[f.name]).items():
                    assert getattr(obj, name) == expected, (spec.sheet, r.row, f.header)
    kept = BranchSetting.objects.filter(branch=branch)
    assert kept.count() == 26 and not kept.filter(key__in=["unit", "periode", "hari_ini", "bulan_ini"]).exists()
    assert (kept.get(key="ambang").value, kept.get(key="nota_awalan").value) == (20000000.0, "SPI-JKT/SPP/")


@pytest.mark.django_db
def test_jakarta_workbook_cannot_go_into_alam_sutera(jkt_data):
    alam_sutera = Branch.objects.create(code="SPI-AS", name="SPI Alam Sutera", city="Tangerang", status="ACTIVE")
    assert any(i.level == "error" and "UNIT-JKT" in i.message for i in validate(jkt_data, alam_sutera))


@pytest.mark.django_db
def test_alam_sutera_imports_as_a_configured_branch_without_operational_data():
    branch = Branch.objects.create(code="SPI-AS", name="(sementara)", status="NEW_BRANCH")
    data = read_workbook(AS)
    assert [i for i in validate(data, branch) if i.level == "error"] == []
    counts = commit_workbook(data, branch, None, replace=False, file_name=AS.name, sha256="-")
    assert {s: n for s, n in counts.items() if n} == {"OFF_REASON_MASTER": 17, "PROGRAM_MASTER": 16, "UNIT_MASTER": 2,
                                                      "TARIF_FEE": 40, "IMPORT_LOG": 1, "AUDIT_LOG": 1}
    branch.refresh_from_db()
    assert (branch.name, branch.city, branch.status, branch.language, branch.currency) == (
        "SPI Alam Sutera", "Tangerang", "ACTIVE", "Indonesia", "IDR")
    kept = set(BranchSetting.objects.filter(branch=branch).values_list("key", flat=True))
    assert len(kept) == 23 and "ambang" in kept and not kept & {"nota_kop", "nota_awalan", "mulai_v4", "branch_name", "unit"}


def test_old_v3_workbook_is_refused():
    with pytest.raises(WorkbookError, match="Bukan workbook SPI v4"):
        read_workbook(V3)
```

- [ ] **Step 2: Jalankan uji — harus gagal**

Run: `.venv/Scripts/python -m pytest importer/tests/test_commit.py importer/tests/test_services.py`
Expected: FAIL (`ModuleNotFoundError: No module named 'importer.commit'`).

- [ ] **Step 3: Model ImportRun**

`importer/models.py`:
```python
from django.conf import settings
from django.db import models


class ImportRun(models.Model):
    """Satu unggahan workbook: pratinjau (belum ada yang disimpan) -> tersimpan / gagal. File di MEDIA_ROOT, tidak dilayani publik."""
    STATUS_CHOICES = [("PREVIEW", "Pratinjau"), ("COMMITTED", "Tersimpan"), ("FAILED", "Gagal")]
    branch = models.ForeignKey("branches.Branch", on_delete=models.CASCADE, related_name="import_runs")
    file = models.FileField(upload_to="imports/%Y/%m/")
    original_name = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=64)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PREVIEW")
    report = models.JSONField(default=dict)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    committed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    committed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.branch.code} · {self.original_name} · {self.status}"
```

Run: `.venv/Scripts/python manage.py makemigrations importer && .venv/Scripts/python manage.py migrate`
Expected: `importer/migrations/0001_initial.py` dengan `Create model ImportRun`.

- [ ] **Step 4: Simpan dalam satu transaksi**

`importer/commit.py`:
```python
"""Menyimpan isi workbook ke database dalam satu transaksi (semua atau tidak sama sekali).

- Tabel Excel: isi cabang diganti isi workbook; row_no = nomor baris sheet (urutan sama dengan Excel).
- Riwayat (AUDIT_LOG, IMPORT_LOG): tidak pernah dihapus/diubah. Baris workbook yang isinya sudah tersimpan dilewati; Log ID Excel dipakai
  kecuali sudah dipakai catatan lain (lalu diberi Log ID berikutnya dan dicatat di IMPORT_LOG).
- SETTINGS (v2_build_sheets.py SET_ROWS): identitas -> Branch; branch_id dicek validasi; unit = Branch.unit_id; baris rumus dihitung web
  (tidak disimpan) kecuali 'ambang' (=ambang menunjuk sel isian CEK_SPP!B3); baris lain -> BranchSetting."""
import datetime

from django.db import transaction
from django.utils import timezone

from audit.models import ImportLog
from branches.models import Branch, BranchSetting
from core import audit
from core.ids import next_id, next_row_no

from .convert import convert
from .schema import load_schema

LOG_TABLES = {"AUDIT_LOG": ("LOG-", 6), "IMPORT_LOG": None}        # (awalan, digit) untuk ID baru bila ID Excel sudah dipakai
IDENTITY_KEYS = {"branch_name": "name", "branch_city": "city", "branch_address": "address", "branch_status": "status",
                 "branch_lang": "language", "branch_currency": "currency", "branch_open": "opening_date"}
NOT_STORED_KEYS = {"branch_id", "unit"}
STORED_FORMULA_KEYS = {"ambang"}
IMPORT_VERSION = "web tahap 1A"


class ImportBlocked(Exception):
    pass


def branch_has_data(branch):
    """Data cabang = baris tabel Excel mana pun (riwayat tidak dihitung) atau parameter SETTINGS."""
    if BranchSetting.objects.filter(branch=branch).exists():
        return True
    return any(s.model_class().objects.filter(branch=branch).exists() for s in load_schema() if s.sheet not in LOG_TABLES)


def _names(spec):
    names = []
    for f in spec.stored_fields:
        names += [f.name, f.text_field] if f.text_field else [f.name]
    return names


def _build(spec, rows, branch):
    model = spec.model_class()
    objs = []
    for r in rows:
        values = {}
        for f in spec.stored_fields:
            values.update(convert(f, r.values.get(f.name)))
        objs.append(model(branch=branch, row_no=r.row, **values))
    return objs


def _replace(spec, rows, branch):
    model = spec.model_class()
    model.objects.filter(branch=branch).delete()
    model.objects.bulk_create(_build(spec, rows, branch), batch_size=1000)
    return len(rows)


def _merge_log(spec, rows, branch):
    model, id_rule = spec.model_class(), LOG_TABLES[spec.sheet]
    content = [n for n in _names(spec) if not (id_rule and n == spec.key)]
    current = list(model.objects.for_branch(branch))
    stored = {tuple(getattr(o, n) for n in content) for o in current}
    used = {getattr(o, spec.key) for o in current}
    last_row = max((o.row_no for o in current), default=None)     # tabel kosong: nomor baris Excel dipakai
    added = renumbered = 0
    for obj in _build(spec, rows, branch):
        if tuple(getattr(obj, n) for n in content) in stored:
            continue
        if id_rule and getattr(obj, spec.key) in used:
            setattr(obj, spec.key, next_id(model, spec.key, *id_rule, branch))
            renumbered += 1
        if last_row is not None:
            last_row += 1
            obj.row_no = last_row
        obj.save()
        used.add(getattr(obj, spec.key))
        added += 1
    return added, renumbered


def _identity_value(field, v):
    if field == "opening_date":
        if isinstance(v, datetime.datetime):
            return v.date()
        return v if isinstance(v, datetime.date) else None
    return "" if v is None else str(v).strip()


def stored_settings(settings):
    """Baris SETTINGS yang disimpan sebagai BranchSetting (juga dipakai template cabang baru, Task 10)."""
    return [s for s in settings if s["key"] not in IDENTITY_KEYS and s["key"] not in NOT_STORED_KEYS
            and (not s["is_formula"] or s["key"] in STORED_FORMULA_KEYS)]


def _apply_settings(data, branch, user):
    changed = []
    for s in data.settings:
        field = IDENTITY_KEYS.get(s["key"])
        if field is None:
            continue
        value = _identity_value(field, s["value"])
        if (field == "name" and not value) or (field == "status" and value not in dict(Branch.STATUS_CHOICES)):
            continue                                   # nama wajib; status dibatasi daftar (validasi data Excel): nilai lama dipakai
        old = getattr(branch, field)
        if old != value:
            setattr(branch, field, value)
            changed.append((field, old, value))
    if changed:
        branch.save(update_fields=[f for f, _old, _new in changed])
        for field, old, value in changed:
            audit.log(branch=branch, user=user, action="UPDATE", entity="CABANG", entity_id=branch.code,
                      field=str(Branch._meta.get_field(field).verbose_name), old=old, new=value)
    BranchSetting.objects.filter(branch=branch).delete()
    BranchSetting.objects.bulk_create([
        BranchSetting(branch=branch, key=s["key"], label=str(s["param"]), note=str(s["note"]), row_no=s["row"],
                      **BranchSetting.split_value(s["value"]))
        for s in stored_settings(data.settings)])


def _log_import(branch, *, file_name, sha256, source_path, counts, notes):
    now = timezone.localtime()
    batch = next_id(ImportLog, "batch", f"IMP-{branch.unit_id[len('UNIT-'):]}-{now:%Y%m%d}-", 2, branch)
    ImportLog.objects.create(
        branch=branch, row_no=next_row_no(ImportLog, branch), batch=batch, date=now.strftime("%Y-%m-%d %H:%M"), file=file_name,
        path=source_path or "unggahan web", sha=sha256, sheets=f"{len(counts)} tabel + SETTINGS",
        rows="; ".join(f"{sheet} {n}" for sheet, n in counts.items() if n) or "0 baris",
        excluded="kolom rumus (dihitung aplikasi web)", ver=IMPORT_VERSION, notes="; ".join(notes))
    return batch


@transaction.atomic
def commit_workbook(data, branch, user, *, replace, file_name, sha256, source_path="", note=""):
    list(Branch.objects.select_for_update().filter(pk=branch.pk).values_list("pk", flat=True))   # satu impor per cabang
    had_data = branch_has_data(branch)
    if had_data and not replace:
        raise ImportBlocked(f"{branch.name} sudah berisi data. Pilih 'ganti semua data cabang' untuk menggantinya dengan isi workbook ini.")
    counts, notes = {}, [n for n in (note, "ganti semua data cabang" if had_data else "") if n]
    for spec in load_schema():
        rows = data.tables.get(spec.sheet, [])
        if spec.sheet in LOG_TABLES:
            counts[spec.sheet], renumbered = _merge_log(spec, rows, branch)
            if renumbered:
                notes.append(f"{renumbered} baris {spec.sheet} workbook mendapat Log ID baru (ID Excel sudah dipakai catatan web)")
        else:
            counts[spec.sheet] = _replace(spec, rows, branch)
    _apply_settings(data, branch, user)                # sesudah riwayat workbook: catatan web mendapat Log ID sesudahnya
    batch = _log_import(branch, file_name=file_name, sha256=sha256, source_path=source_path, counts=counts, notes=notes)
    audit.log(branch=branch, user=user, action="IMPORT", entity="WORKBOOK", entity_id=file_name,
              new=" · ".join([batch, f"{sum(counts.values())} baris", *notes]))
    return counts
```

- [ ] **Step 5: Alur pratinjau → simpan**

`importer/services.py`:
```python
"""Alur impor web: unggah -> baca & validasi (pratinjau; belum ada yang disimpan) -> simpan (satu transaksi)."""
import hashlib

from django.db import transaction
from django.utils import timezone

from .commit import ImportBlocked, branch_has_data, commit_workbook
from .models import ImportRun
from .reader import WorkbookError, read_workbook
from .schema import load_schema
from .validate import validate

MAX_ISSUES = 500
GROUPS = (("students", "Murid"), ("classes", "Kelas"), ("finance", "Keuangan"), ("masterdata", "Master data"),
          ("quality", "Kualitas data"), ("audit", "Riwayat & audit"))


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def existing_counts(branch):
    return {s.sheet: s.model_class().objects.filter(branch=branch).count() for s in load_schema()}


def build_report(path, branch):
    base = {"ok": False, "fatal": "", "unit": "", "counts": {}, "errors": 0, "warnings": 0, "issues": [], "issues_hidden": 0,
            "existing": existing_counts(branch), "has_data": branch_has_data(branch)}
    try:
        data = read_workbook(path)
    except WorkbookError as exc:
        return {**base, "fatal": str(exc), "errors": 1}
    issues = sorted(validate(data, branch), key=lambda i: (i.level != "error", i.table, i.row or 0))
    errors = sum(1 for i in issues if i.level == "error")
    return {**base, "ok": errors == 0, "unit": data.unit or "", "errors": errors, "warnings": len(issues) - errors,
            "counts": {s.sheet: len(data.tables.get(s.sheet, [])) for s in load_schema()},
            "issues": [i.as_dict() for i in issues[:MAX_ISSUES]], "issues_hidden": max(0, len(issues) - MAX_ISSUES)}


def create_run(uploaded_file, branch, user):
    run = ImportRun(branch=branch, original_name=uploaded_file.name[:255], created_by=user)
    run.file.save(uploaded_file.name, uploaded_file, save=False)
    run.sha256 = sha256_of(run.file.path)
    run.report = build_report(run.file.path, branch)
    run.save()
    return run


def commit_run(run, user, *, replace):
    try:
        with transaction.atomic():
            run = ImportRun.objects.select_for_update().get(pk=run.pk)
            if run.status != "PREVIEW":
                raise ImportBlocked("Impor ini sudah diproses - unggah ulang file bila perlu.")
            if not run.report.get("ok") or sha256_of(run.file.path) != run.sha256:
                raise ImportBlocked("Workbook ini punya error atau berubah sejak pratinjau - perbaiki di Excel lalu unggah ulang.")
            data = read_workbook(run.file.path)
            if any(i.level == "error" for i in validate(data, run.branch)):
                raise ImportBlocked("Workbook ini punya error - perbaiki di Excel lalu unggah ulang.")
            counts = commit_workbook(data, run.branch, user, replace=replace, file_name=run.original_name, sha256=run.sha256)
            run.status, run.committed_by, run.committed_at = "COMMITTED", user, timezone.now()
            run.report = {**run.report, "saved": counts}
            run.save(update_fields=["status", "committed_by", "committed_at", "report"])
    except ImportBlocked:
        raise
    except Exception:
        ImportRun.objects.filter(pk=run.pk, status="PREVIEW").update(status="FAILED")
        raise
    return counts


def grouped_counts(report):
    out = []
    for app, label in GROUPS:
        tables = [{"sheet": s.sheet, "new": report["counts"].get(s.sheet, 0), "existing": report["existing"].get(s.sheet, 0),
                   "saved": report.get("saved", {}).get(s.sheet)} for s in load_schema() if s.app == app]
        out.append({"label": label, "tables": tables, "new": sum(t["new"] for t in tables),
                    "existing": sum(t["existing"] for t in tables)})
    return out
```

- [ ] **Step 6: Perintah impor (migrasi Jakarta / Alam Sutera)**

`importer/management/__init__.py`, `importer/management/commands/__init__.py`: kosong.

`importer/management/commands/import_workbook.py`:
```python
"""Impor workbook SPI v4 dari baris perintah. Tanpa --commit hanya pratinjau (tidak ada yang disimpan).
    .venv/Scripts/python manage.py import_workbook ../APP/SPI_ALAM_SUTERA_v4.xlsm --branch SPI-AS --create --commit"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from branches.models import Branch
from importer.commit import ImportBlocked, commit_workbook
from importer.reader import WorkbookError, read_workbook
from importer.services import sha256_of
from importer.validate import validate

SHOW = 50


class Command(BaseCommand):
    help = "Baca & validasi workbook SPI v4; dengan --commit simpan ke cabang dalam satu transaksi."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--branch", required=True, help="Branch ID, mis. SPI-JKT")
        parser.add_argument("--create", action="store_true", help="buat cabang bila belum ada")
        parser.add_argument("--name", default="", help="nama cabang baru (bawaan: 'Nama cabang' di SETTINGS workbook)")
        parser.add_argument("--city", default="", help="kota cabang baru (bawaan: 'Kota' di SETTINGS workbook)")
        parser.add_argument("--status", default="", choices=["", *dict(Branch.STATUS_CHOICES)],
                            help="status cabang baru (bawaan: 'Status cabang' di SETTINGS workbook, lalu NEW_BRANCH)")
        parser.add_argument("--commit", action="store_true", help="simpan; tanpa ini hanya pratinjau")
        parser.add_argument("--replace", action="store_true", help="ganti semua data cabang yang sudah ada")

    def handle(self, *args, **opts):
        path, code = Path(opts["path"]), opts["branch"].strip().upper()
        try:
            data = read_workbook(path)
        except WorkbookError as exc:
            raise CommandError(str(exc)) from exc
        with transaction.atomic():
            branch = Branch.objects.filter(code=code).first()
            created = branch is None
            if created:
                if not opts["create"]:
                    raise CommandError(f"Cabang {code} belum ada - tambahkan --create untuk membuatnya.")
                setting = lambda key: str((data.setting(key) or {}).get("value") or "").strip()   # noqa: E731
                status = opts["status"] or setting("branch_status")
                branch = Branch.objects.create(code=code, name=opts["name"] or setting("branch_name") or code,
                                               city=opts["city"] or setting("branch_city"),
                                               status=status if status in dict(Branch.STATUS_CHOICES) else "NEW_BRANCH")
            issues = validate(data, branch)
            for i in issues[:SHOW]:
                self.stdout.write(f"  {i.level.upper():7} {i.table} baris {i.row or '-'} [{i.field}] {i.message}")
            errors = sum(1 for i in issues if i.level == "error")
            self.stdout.write(f"{len(issues) - SHOW} temuan lain tidak ditampilkan." if len(issues) > SHOW else "")
            self.stdout.write("Baris: " + ", ".join(f"{sheet} {len(rows)}" for sheet, rows in data.tables.items() if rows))
            self.stdout.write(f"Error {errors} · peringatan {len(issues) - errors}")
            if errors:
                raise CommandError("Workbook punya error - tidak ada yang disimpan.")
            if not opts["commit"]:
                transaction.set_rollback(True)
                self.stdout.write("Pratinjau saja - tidak ada yang disimpan. Tambahkan --commit untuk menyimpan.")
                return
            try:
                counts = commit_workbook(data, branch, None, replace=opts["replace"], file_name=path.name, sha256=sha256_of(path),
                                         source_path=str(path), note="cabang dibuat dari workbook" if created else "")
            except ImportBlocked as exc:
                raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Tersimpan ke {branch.code}: {sum(counts.values())} baris."))
```

- [ ] **Step 7: Jalankan uji**

Run: `.venv/Scripts/python -m pytest importer`
Expected: semua lulus (termasuk 6 uji simpan, 3 uji layanan & perintah).

Run (workbook asli, beberapa menit): `.venv/Scripts/python -m pytest -m slow importer/tests/test_real_workbooks.py`
Expected: `4 passed`. Angka uji berasal dari workbook saat rencana ditulis (SHA-256 `sha256sum ../APP/*.xlsm`: Jakarta v4 `9d53801243ef56879e623ef54f0c91541696c75618fe80a4cfaddfa6c64092b9`, Alam Sutera `8dc4ba0ae61f40f2b0f5a32644fef4b726562d35b531a80973bf727736291ef7`). Bila uji gagal karena jumlah baris, cek dulu apakah workbook sudah berubah sebelum mengubah angka uji.

- [ ] **Step 8: Commit**

```bash
git add importer
git commit -m "feat: simpan impor dalam satu transaksi, riwayat audit tidak pernah hilang, perintah import_workbook" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Halaman Impor Data — unggah, pratinjau, simpan

**Files:**
- Create: `importer/forms.py`, `importer/views.py`, `importer/urls.py`
- Create: `importer/templates/importer/upload.html`, `importer/templates/importer/preview.html`, `importer/templates/importer/_status.html`
- Create: `importer/tests/test_views.py`
- Modify: `spi_web/urls.py`

**Interfaces:**
- Consumes: `require_cap`, `Cap.BRANCH_ADMIN` (Task 5); `create_run`, `commit_run`, `existing_counts`, `grouped_counts`, `ImportBlocked`, `branch_has_data`, `ImportRun` (Task 8).
- Produces: URL `importer:upload` (`/impor/`), `importer:preview` (`/impor/<pk>/`), `importer:commit` (`/impor/<pk>/simpan/`, POST, `replace=on`); `importer.forms.UploadForm` (`MAX_UPLOAD_MB = 40`).

- [ ] **Step 1: Tulis uji yang gagal**

`importer/tests/test_views.py`:
```python
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from importer.models import ImportRun
from importer.tests.factories import build_workbook
from students.models import StudentMaster

STUDENTS = {"STUDENT_MASTER": [{"Student ID": "STD-000001", "Nama Murid": "Ani"}]}


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture
def admin_client(client, branch, make_user):
    client.force_login(make_user("admin@spi.test", role="BRANCH_ADMIN", branch=branch))
    return client


def workbook_file(tmp_path, settings=None):
    return SimpleUploadedFile("jkt.xlsm", build_workbook(tmp_path / "wb.xlsx", STUDENTS, settings).read_bytes())


@pytest.mark.django_db
def test_only_branch_admin_can_import(client, branch, make_user):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    assert client.get(reverse("importer:upload")).status_code == 403


@pytest.mark.django_db
def test_upload_shows_a_preview_and_saves_nothing_until_confirmed(admin_client, tmp_path, branch):
    response = admin_client.post(reverse("importer:upload"), {"file": workbook_file(tmp_path)})
    run = ImportRun.objects.get()
    assert response.status_code == 302 and response.url == reverse("importer:preview", args=[run.pk])
    page = admin_client.get(response.url).content.decode()
    assert "STUDENT_MASTER" in page and "Simpan ke database" in page and "sudah berisi data" not in page
    assert not StudentMaster.objects.exists()
    page = admin_client.post(reverse("importer:commit", args=[run.pk]), follow=True).content.decode()
    assert "Tersimpan ke SPI Jakarta" in page
    assert StudentMaster.objects.for_branch(branch).count() == 1


@pytest.mark.django_db
def test_import_into_a_branch_with_data_needs_the_replace_checkbox(admin_client, tmp_path, branch):
    for _ in range(2):
        admin_client.post(reverse("importer:upload"), {"file": workbook_file(tmp_path)})
    first, second = ImportRun.objects.order_by("pk")
    admin_client.post(reverse("importer:commit", args=[first.pk]))
    assert "sudah berisi data" in admin_client.get(reverse("importer:preview", args=[second.pk])).content.decode()
    page = admin_client.post(reverse("importer:commit", args=[second.pk]), follow=True).content.decode()
    assert "ganti semua data cabang" in page
    second.refresh_from_db()
    assert second.status == "PREVIEW"
    admin_client.post(reverse("importer:commit", args=[second.pk]), {"replace": "on"})
    second.refresh_from_db()
    assert second.status == "COMMITTED" and StudentMaster.objects.for_branch(branch).count() == 1


@pytest.mark.django_db
def test_imports_of_another_branch_are_not_found(admin_client, other_branch):
    run = ImportRun.objects.create(branch=other_branch, original_name="as.xlsm", sha256="0" * 64, report={"ok": True})
    assert admin_client.get(reverse("importer:preview", args=[run.pk])).status_code == 404
    assert admin_client.post(reverse("importer:commit", args=[run.pk]), {"replace": "on"}).status_code == 404


@pytest.mark.django_db
def test_file_that_is_not_excel_is_refused_by_the_form(admin_client):
    response = admin_client.post(reverse("importer:upload"), {"file": SimpleUploadedFile("murid.csv", b"a,b")})
    assert response.status_code == 200 and "Pilih file Excel" in response.content.decode()
    assert not ImportRun.objects.exists()


@pytest.mark.django_db
def test_workbook_of_another_branch_shows_the_error_and_cannot_be_saved(admin_client, tmp_path):
    admin_client.post(reverse("importer:upload"), {"file": workbook_file(tmp_path, settings={"unit": "UNIT-AS"})})
    run = ImportRun.objects.get()
    page = admin_client.get(reverse("importer:preview", args=[run.pk])).content.decode()
    assert "bukan UNIT-JKT" in page and "Simpan ke database" not in page
    admin_client.post(reverse("importer:commit", args=[run.pk]))
    assert not StudentMaster.objects.exists()
```

- [ ] **Step 2: Jalankan uji — harus gagal**

Run: `.venv/Scripts/python -m pytest importer/tests/test_views.py`
Expected: FAIL (`NoReverseMatch: 'importer' is not a registered namespace`).

- [ ] **Step 3: Form, view, URL**

`importer/forms.py`:
```python
from django import forms

MAX_UPLOAD_MB = 40


class UploadForm(forms.Form):
    file = forms.FileField(label="Workbook SPI v4 (.xlsm / .xlsx)")

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.lower().endswith((".xlsm", ".xlsx")):
            raise forms.ValidationError("Pilih file Excel .xlsm atau .xlsx (workbook SPI v4).")
        if f.size > MAX_UPLOAD_MB * 1024 * 1024:
            raise forms.ValidationError(f"File lebih besar dari {MAX_UPLOAD_MB} MB.")
        return f
```

`importer/views.py`:
```python
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.capabilities import Cap
from core.decorators import require_cap

from .commit import ImportBlocked, branch_has_data
from .forms import UploadForm
from .models import ImportRun
from .services import commit_run, create_run, existing_counts, grouped_counts


@require_cap(Cap.BRANCH_ADMIN)
def upload(request):
    form = UploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        run = create_run(form.cleaned_data["file"], request.branch, request.user)
        return redirect("importer:preview", pk=run.pk)
    runs = ImportRun.objects.filter(branch=request.branch).select_related("created_by")[:10]
    return render(request, "importer/upload.html", {"form": form, "runs": runs})


@require_cap(Cap.BRANCH_ADMIN)
def preview(request, pk):
    run = get_object_or_404(ImportRun.objects.select_related("created_by", "committed_by"), pk=pk, branch=request.branch)
    report = dict(run.report)
    if run.status == "PREVIEW":
        report["existing"] = existing_counts(request.branch)            # keadaan cabang saat ini, bukan saat unggah
    groups = grouped_counts(report) if report.get("counts") else []
    return render(request, "importer/preview.html", {"run": run, "report": report, "groups": groups,
                                                     "has_data": branch_has_data(request.branch)})


@require_POST
@require_cap(Cap.BRANCH_ADMIN)
def commit(request, pk):
    run = get_object_or_404(ImportRun, pk=pk, branch=request.branch)
    try:
        counts = commit_run(run, request.user, replace=request.POST.get("replace") == "on")
    except ImportBlocked as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"Tersimpan ke {request.branch.name}: {sum(counts.values())} baris dari {run.original_name}.")
    return redirect("importer:preview", pk=run.pk)
```

`importer/urls.py`:
```python
from django.urls import path

from . import views

app_name = "importer"
urlpatterns = [
    path("", views.upload, name="upload"),
    path("<int:pk>/", views.preview, name="preview"),
    path("<int:pk>/simpan/", views.commit, name="commit"),
]
```

Modify `spi_web/urls.py` — tambahkan ke `urlpatterns`:
```python
    path("impor/", include("importer.urls")),
```

- [ ] **Step 4: Template**

`importer/templates/importer/_status.html`:
```html
{% if run.status == "COMMITTED" %}<span class="badge bg-emerald-50 text-emerald-700">Tersimpan</span>
{% elif run.status == "FAILED" %}<span class="badge bg-red-50 text-red-700">Gagal</span>
{% elif run.report.ok %}<span class="badge bg-brand-50 text-brand-700">Pratinjau</span>
{% else %}<span class="badge bg-red-50 text-red-700">Ada error</span>{% endif %}
```

`importer/templates/importer/upload.html`:
```html
{% extends "base.html" %}
{% block title %}Impor Data{% endblock %}
{% block content %}
<h1 class="text-2xl font-semibold text-slate-900">Impor Data <span class="text-base font-normal text-slate-500">· {{ current_branch.name }}</span></h1>
<p class="mb-6 mt-1 max-w-3xl text-sm text-slate-500">Unggah workbook SPI v4 milik cabang ini. Aplikasi membaca setiap tabel lewat judul kolomnya, memeriksa isinya,
  lalu menampilkan pratinjau. Belum ada yang disimpan sampai Anda menekan tombol simpan di halaman pratinjau.</p>
<div class="grid gap-6 lg:grid-cols-3">
  <form method="post" enctype="multipart/form-data" class="card form space-y-4 p-5" x-data="{ busy: false }" @submit="busy = true">{% csrf_token %}
    <h2 class="font-semibold">Unggah workbook</h2>
    {% for field in form %}<div>{{ field.label_tag }}{{ field }}{{ field.errors }}</div>{% endfor %}
    <button class="btn btn-primary w-full" :disabled="busy"><span x-show="!busy">Baca &amp; periksa</span><span x-show="busy" x-cloak>Membaca workbook…</span></button>
  </form>
  <div class="card overflow-hidden lg:col-span-2">
    <h2 class="border-b border-slate-200 px-4 py-3 font-semibold">Unggahan terakhir</h2>
    <table class="min-w-full divide-y divide-slate-200 text-sm">
      <thead class="bg-slate-50 text-left text-xs font-semibold uppercase text-slate-500">
        <tr><th class="px-4 py-2">Waktu</th><th class="px-4 py-2">File</th><th class="px-4 py-2">Oleh</th><th class="px-4 py-2">Status</th></tr></thead>
      <tbody class="divide-y divide-slate-100">
        {% for r in runs %}
          <tr><td class="px-4 py-2 text-slate-600">{{ r.created_at|date:"d M Y H:i" }}</td>
            <td class="px-4 py-2"><a href="{% url 'importer:preview' r.pk %}" class="font-medium text-brand-600 hover:underline">{{ r.original_name }}</a></td>
            <td class="px-4 py-2 text-slate-600">{{ r.created_by.display_name|default:"-" }}</td>
            <td class="px-4 py-2">{% include "importer/_status.html" with run=r %}</td></tr>
        {% empty %}<tr><td colspan="4" class="px-4 py-6 text-center text-slate-500">Belum ada unggahan.</td></tr>{% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
```

`importer/templates/importer/preview.html`:
```html
{% extends "base.html" %}
{% block title %}Pratinjau impor{% endblock %}
{% block content %}
<a href="{% url 'importer:upload' %}" class="text-sm font-semibold text-brand-600 hover:underline">← Impor Data</a>
<div class="mb-6 mt-2 flex flex-wrap items-start justify-between gap-4">
  <div>
    <h1 class="text-2xl font-semibold text-slate-900">{{ run.original_name }}</h1>
    <p class="text-sm text-slate-500">ke {{ current_branch.name }} · diunggah {{ run.created_at|date:"d M Y H:i" }} oleh {{ run.created_by.display_name|default:"-" }}
      · SHA-256 <code class="text-xs">{{ run.sha256|truncatechars:17 }}</code></p>
  </div>
  {% include "importer/_status.html" %}
</div>

{% if report.fatal %}
  <div class="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-800">{{ report.fatal }}</div>
{% else %}
  <div class="mb-6 grid gap-4 sm:grid-cols-3">
    <div class="card p-4"><p class="text-xs text-slate-500">Unit workbook</p><p class="mt-1 text-lg font-semibold">{{ report.unit|default:"(tidak tercatat)" }}</p></div>
    <div class="card p-4"><p class="text-xs text-slate-500">Error</p><p class="mt-1 text-lg font-semibold {% if report.errors %}text-red-700{% else %}text-emerald-700{% endif %}">{{ report.errors }}</p></div>
    <div class="card p-4"><p class="text-xs text-slate-500">Peringatan</p><p class="mt-1 text-lg font-semibold {% if report.warnings %}text-amber-700{% endif %}">{{ report.warnings }}</p></div>
  </div>

  {% if run.status == "PREVIEW" and report.ok %}
    <form method="post" action="{% url 'importer:commit' run.pk %}" class="card mb-6 space-y-3 p-5" x-data="{ busy: false }" @submit="busy = true">{% csrf_token %}
      {% if has_data %}
        <div class="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <strong>{{ current_branch.name }} sudah berisi data.</strong> Menyimpan akan mengganti isi semua tabel cabang ini dengan isi workbook.
          Riwayat Audit Log dan Import Log tidak dihapus.</div>
        <label class="flex items-center gap-2 text-sm font-medium text-slate-800">
          <input type="checkbox" name="replace" class="h-4 w-4 rounded border-slate-300"> Ganti semua data cabang ini dengan isi workbook</label>
      {% endif %}
      <button class="btn btn-primary" :disabled="busy"><span x-show="!busy">Simpan ke database</span><span x-show="busy" x-cloak>Menyimpan…</span></button>
    </form>
  {% elif run.status == "COMMITTED" %}
    <div class="mb-6 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
      Tersimpan {{ run.committed_at|date:"d M Y H:i" }} oleh {{ run.committed_by.display_name|default:"-" }}.</div>
  {% endif %}

  <div class="grid gap-6 lg:grid-cols-2">
    <div class="card overflow-hidden">
      <h2 class="border-b border-slate-200 px-4 py-3 font-semibold">Baris per tabel</h2>
      <table class="min-w-full text-sm">
        <thead class="bg-slate-50 text-left text-xs font-semibold uppercase text-slate-500">
          <tr><th class="px-4 py-2">Tabel</th><th class="px-4 py-2 text-right">Di workbook</th>
            <th class="px-4 py-2 text-right">{% if run.status == "COMMITTED" %}Disimpan{% else %}Di cabang sekarang{% endif %}</th></tr></thead>
        <tbody>
          {% for g in groups %}
            <tr class="border-t border-slate-200 bg-slate-50/60"><td colspan="3" class="px-4 py-2 text-xs font-semibold uppercase text-slate-500">{{ g.label }}</td></tr>
            {% for t in g.tables %}
              <tr class="border-t border-slate-100"><td class="px-4 py-1.5 font-mono text-xs">{{ t.sheet }}</td>
                <td class="px-4 py-1.5 text-right tabular-nums">{{ t.new }}</td>
                <td class="px-4 py-1.5 text-right tabular-nums">{% if run.status == "COMMITTED" %}{{ t.saved|default_if_none:"-" }}{% else %}{{ t.existing }}{% endif %}</td></tr>
            {% endfor %}
          {% endfor %}
        </tbody>
      </table>
    </div>
    <div class="card overflow-hidden">
      <h2 class="border-b border-slate-200 px-4 py-3 font-semibold">Temuan pemeriksaan</h2>
      {% if report.issues %}
        <div class="max-h-[40rem] overflow-y-auto">
          <table class="min-w-full text-sm">
            <thead class="sticky top-0 bg-slate-50 text-left text-xs font-semibold uppercase text-slate-500">
              <tr><th class="px-4 py-2">Tingkat</th><th class="px-4 py-2">Tabel</th><th class="px-4 py-2">Baris</th><th class="px-4 py-2">Kolom</th><th class="px-4 py-2">Pesan</th></tr></thead>
            <tbody class="divide-y divide-slate-100">
              {% for i in report.issues %}
                <tr><td class="px-4 py-2">{% if i.level == "error" %}<span class="badge bg-red-50 text-red-700">Error</span>{% else %}<span class="badge bg-amber-50 text-amber-800">Peringatan</span>{% endif %}</td>
                  <td class="px-4 py-2 font-mono text-xs">{{ i.table }}</td><td class="px-4 py-2 tabular-nums">{{ i.row|default:"-" }}</td>
                  <td class="px-4 py-2">{{ i.field }}</td><td class="px-4 py-2">{{ i.message }}</td></tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
        {% if report.issues_hidden %}<p class="border-t border-slate-200 px-4 py-2 text-xs text-slate-500">{{ report.issues_hidden }} temuan lain tidak ditampilkan.</p>{% endif %}
      {% else %}
        <p class="px-4 py-6 text-sm text-emerald-700">Tidak ada temuan.</p>
      {% endif %}
    </div>
  </div>
{% endif %}
{% endblock %}
```

Run: `npm run build:css`

- [ ] **Step 5: Jalankan uji**

Run: `.venv/Scripts/python -m pytest`
Expected: semua lulus (termasuk 6 uji halaman impor).

- [ ] **Step 6: Commit**

```bash
git add importer spi_web/urls.py static/css/app.css
git commit -m "feat: halaman Impor Data - unggah, pratinjau per tabel & temuan, simpan dengan konfirmasi ganti" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Cabang baru dari template (SUPER_ADMIN)

**Files:**
- Create: `tools/export_template_config.py`, `branches/template_config.json` (hasil ekspor), `branches/services.py`, `branches/forms.py`, `branches/views.py`, `branches/urls.py`, `branches/templates/branches/list.html`
- Create: `branches/tests/test_create_branch.py`, `branches/tests/test_branch_views.py`, `branches/tests/test_template_matches_workbook.py`
- Modify: `core/decorators.py` (`require_super_admin`), `core/nav.py` (menu SUPER_ADMIN tanpa cabang aktif), `core/templates/core/no_access.html`, `spi_web/urls.py`

**Interfaces:**
- Consumes: `read_workbook` (Task 7); `stored_settings`, `LOG_TABLES`, `IMPORT_VERSION`, `commit_workbook` (Task 8); `convert`, `table`, `load_schema`; `next_id`, `next_row_no`, `audit.log` (Task 4).
- Produces:
  - `branches/template_config.json` (`source` {workbook, sha256}, `unit_placeholder`, `tables` {sheet: [{row, values}]}, `settings` [{key, param, value, note, row}])
  - `branches.services.template_config() -> dict`; `create_branch(*, code, name, city="", address="", status="NEW_BRANCH", language="Indonesia", currency="IDR", opening_date=None, user=None) -> Branch`
  - `core.decorators.require_super_admin(view)`; URL `branches:list` (`/cabang/`, GET daftar + POST buat cabang)

Aturan (sama dengan `branch_model.py` pipeline): cabang baru = identitas (8 kolom) + konfigurasi SPI yang disalin dari template (16 program & level, 17 kategori OFF, unit cabang + unit pusat, 40 kunci tarif fee, parameter SETTINGS); baris unit `UNIT-XXX` diisi identitas cabang (Unit ID, nama, kota, status); tabel operasional kosong; satu baris IMPORT_LOG (`IMP-<kode>-<yyyymmdd>-NN`, juga nilai parameter `batch`) dan satu baris AUDIT_LOG `CREATE`.

- [ ] **Step 1: Tulis uji yang gagal**

`branches/tests/test_create_branch.py`:
```python
import re

import pytest

from audit.models import AuditLog, ImportLog
from branches.models import BranchSetting
from branches.services import create_branch
from importer.schema import load_schema
from masterdata.models import UnitMaster


@pytest.mark.django_db
def test_new_branch_gets_the_spi_configuration_and_no_operational_data(make_user):
    boss = make_user("boss@spi.test", super_admin=True)
    branch = create_branch(code="spi-bsd", name="SPI BSD", city="Tangerang Selatan", user=boss)
    assert (branch.code, branch.unit_id, branch.status) == ("SPI-BSD", "UNIT-BSD", "NEW_BRANCH")
    counts = {s.sheet: s.model_class().objects.for_branch(branch).count() for s in load_schema()}
    assert {s: n for s, n in counts.items() if n} == {"PROGRAM_MASTER": 16, "OFF_REASON_MASTER": 17, "UNIT_MASTER": 2,
                                                      "TARIF_FEE": 40, "IMPORT_LOG": 1, "AUDIT_LOG": 1}
    unit = UnitMaster.objects.for_branch(branch).get(uid="UNIT-BSD")
    assert (unit.name, unit.city, unit.status, unit.parent) == ("SPI BSD", "Tangerang Selatan", "NEW_BRANCH", "UNIT-HQ")
    batch = ImportLog.objects.for_branch(branch).get().batch
    assert re.fullmatch(r"IMP-BSD-\d{8}-01", batch)
    settings = {s.key: s.value for s in BranchSetting.objects.filter(branch=branch)}
    assert len(settings) == 23 and settings["batch"] == batch
    assert (settings["F"], settings["S"], settings["off_lama"], settings["ambang"]) == (1.0, 20.0, 3.0, 20000000.0)
    log = AuditLog.objects.for_branch(branch).get()
    assert (log.lid, log.action, log.entity, log.eid, log.user) == ("LOG-000001", "CREATE", "CABANG", "SPI-BSD", "Boss")


@pytest.mark.django_db
def test_branches_created_from_the_template_are_independent():
    one = create_branch(code="SPI-AA", name="SPI AA")
    two = create_branch(code="SPI-BB", name="SPI BB")
    assert UnitMaster.objects.for_branch(one).filter(uid="UNIT-BB").count() == 0
    assert set(UnitMaster.objects.for_branch(two).values_list("uid", flat=True)) == {"UNIT-BB", "UNIT-HQ"}
```

`branches/tests/test_branch_views.py`:
```python
import datetime

import pytest
from django.urls import reverse

from branches.models import Branch
from masterdata.models import ProgramMaster

NEW = {"code": "spi-as", "name": "SPI Alam Sutera", "city": "Tangerang", "address": "", "status": "NEW_BRANCH",
       "language": "Indonesia", "currency": "IDR", "opening_date": "2026-11-01"}


@pytest.mark.django_db
def test_only_super_admin_manages_branches(client, branch, make_user):
    client.force_login(make_user("admin@spi.test", role="BRANCH_ADMIN", branch=branch))
    assert client.get(reverse("branches:list")).status_code == 403
    assert client.post(reverse("branches:list"), NEW).status_code == 403
    assert not Branch.objects.filter(code="SPI-AS").exists()


@pytest.mark.django_db
def test_super_admin_creates_the_first_branch_without_an_active_branch(client, make_user):
    client.force_login(make_user("boss@spi.test", super_admin=True))
    assert "Buat cabang pertama" in client.get("/").content.decode()
    assert "Buat cabang baru" in client.get(reverse("branches:list")).content.decode()
    response = client.post(reverse("branches:list"), NEW)
    assert response.status_code == 302
    branch = Branch.objects.get(code="SPI-AS")
    assert branch.opening_date == datetime.date(2026, 11, 1)
    assert ProgramMaster.objects.for_branch(branch).count() == 16
    assert client.get("/").status_code == 200                       # satu-satunya cabang langsung aktif


@pytest.mark.django_db
def test_branch_code_format_and_uniqueness(client, branch, make_user):
    client.force_login(make_user("boss@spi.test", super_admin=True))
    for code, message in (("AS", "Format Branch ID"), ("spi-jkt", "sudah dipakai")):
        response = client.post(reverse("branches:list"), {**NEW, "code": code})
        assert response.status_code == 200 and message in response.content.decode()
    assert Branch.objects.count() == 1
```

`branches/tests/test_template_matches_workbook.py`:
```python
"""Cabang baru web = cabang baru Excel. Memakai workbook asli di ..\\APP (hanya dibaca):
    .venv/Scripts/python -m pytest -m slow branches/tests/test_template_matches_workbook.py"""
import hashlib

import pytest
from django.conf import settings
from django.db import transaction

from branches.models import Branch, BranchSetting
from branches.services import create_branch, template_config
from importer.commit import LOG_TABLES, commit_workbook
from importer.reader import read_workbook
from importer.schema import load_schema

pytestmark = pytest.mark.slow


def snapshot(branch):
    branch.refresh_from_db()
    out = {"branch": [getattr(branch, f) for f in ("name", "city", "address", "status", "language", "currency", "opening_date")]}
    for spec in load_schema():
        if spec.sheet in LOG_TABLES:
            continue
        names = [n for f in spec.stored_fields for n in ([f.name, f.text_field] if f.text_field else [f.name])]
        out[spec.sheet] = [(o.row_no, *[getattr(o, n) for n in names]) for o in spec.model_class().objects.for_branch(branch)]
    out["SETTINGS"] = sorted((s.key, s.label, s.value, s.note, s.row_no) for s in BranchSetting.objects.filter(branch=branch)
                             if s.key != "batch")
    return out


def test_template_config_comes_from_the_current_template_workbook():
    path = settings.SPI_EXCEL_DIR / "SPI_BRANCH_TEMPLATE_v4.xlsm"
    assert template_config()["source"]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.django_db
def test_new_branch_from_the_template_equals_the_alam_sutera_workbook():
    with transaction.atomic():
        made = snapshot(create_branch(code="SPI-AS", name="SPI Alam Sutera", city="Tangerang", status="ACTIVE"))
        transaction.set_rollback(True)                                # buang; kode SPI-AS dipakai lagi di bawah
    branch = Branch.objects.create(code="SPI-AS", name="(sementara)")
    commit_workbook(read_workbook(settings.SPI_EXCEL_DIR / "SPI_ALAM_SUTERA_v4.xlsm"), branch, None, replace=False,
                    file_name="SPI_ALAM_SUTERA_v4.xlsm", sha256="-")
    assert snapshot(branch) == made
```

- [ ] **Step 2: Jalankan uji — harus gagal**

Run: `.venv/Scripts/python -m pytest branches`
Expected: FAIL (`ModuleNotFoundError: No module named 'branches.services'`).

- [ ] **Step 3: Ekspor konfigurasi template**

`tools/export_template_config.py`:
```python
"""Ekspor konfigurasi SPI dari SPI_BRANCH_TEMPLATE_v4.xlsm ke branches/template_config.json (alat pengembang, hanya membaca workbook).
Isi = tabel yang tidak kosong di template (program & level, kategori OFF, unit, kunci tarif fee) + parameter SETTINGS yang disimpan per
cabang (aturan importer.commit.stored_settings). Template tidak berisi data operasional.
    .venv/Scripts/python tools/export_template_config.py"""
import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WEB))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spi_web.settings")
import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402

from importer.commit import LOG_TABLES, stored_settings  # noqa: E402
from importer.reader import read_workbook  # noqa: E402

SOURCE = settings.SPI_EXCEL_DIR / "SPI_BRANCH_TEMPLATE_v4.xlsm"
OUT = WEB / "branches" / "template_config.json"
UNIT_PLACEHOLDER = "UNIT-XXX"


def plain(value, where):
    if isinstance(value, (datetime.date, datetime.time)):
        raise SystemExit(f"{where}: nilai tanggal/jam belum didukung template_config.json - tambahkan penanganannya dulu")
    return value


def main():
    data = read_workbook(SOURCE)
    tables = {sheet: [{"row": r.row, "values": {k: plain(v, f"{sheet} baris {r.row}") for k, v in r.values.items()}} for r in rows]
              for sheet, rows in data.tables.items() if rows and sheet not in LOG_TABLES}
    assert UNIT_PLACEHOLDER in [r["values"]["uid"] for r in tables["UNIT_MASTER"]], "baris unit template tidak ditemukan"
    rows = [{"key": s["key"], "param": s["param"], "value": plain(s["value"], f"SETTINGS {s['key']}"), "note": s["note"], "row": s["row"]}
            for s in stored_settings(data.settings)]
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    OUT.write_text(json.dumps({"source": {"workbook": SOURCE.name, "sha256": digest}, "unit_placeholder": UNIT_PLACEHOLDER,
                               "tables": tables, "settings": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("tabel", {sheet: len(r) for sheet, r in tables.items()}, "| parameter", len(rows), "| sha256", digest[:12])


if __name__ == "__main__":
    main()
```

Run: `.venv/Scripts/python tools/export_template_config.py`
Expected: `tabel {'OFF_REASON_MASTER': 17, 'PROGRAM_MASTER': 16, 'UNIT_MASTER': 2, 'TARIF_FEE': 40} | parameter 23 | sha256 6ff4b6bf2b20`

- [ ] **Step 4: Layanan buat cabang**

`branches/services.py`:
```python
"""Cabang baru dari template (setara SPI_BRANCH_TEMPLATE_v4.xlsm + branch_model.py): identitas + konfigurasi SPI, tanpa data operasional."""
import json
from functools import lru_cache
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from audit.models import ImportLog
from core import audit
from core.ids import next_id, next_row_no
from importer.commit import IMPORT_VERSION
from importer.convert import convert
from importer.schema import table

from .models import Branch, BranchSetting

TEMPLATE_PATH = Path(__file__).resolve().parent / "template_config.json"


@lru_cache(maxsize=1)
def template_config():
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def _typed(spec, raw):
    values = {}
    for f in spec.stored_fields:
        values.update(convert(f, raw.get(f.name)))
    return values


@transaction.atomic
def create_branch(*, code, name, city="", address="", status="NEW_BRANCH", language="Indonesia", currency="IDR", opening_date=None,
                  user=None):
    cfg = template_config()
    branch = Branch.objects.create(code=code.strip().upper(), name=name.strip(), city=city, address=address, status=status,
                                   language=language, currency=currency, opening_date=opening_date)
    for sheet, rows in cfg["tables"].items():
        spec = table(sheet)
        model = spec.model_class()
        objs = []
        for r in rows:
            raw = dict(r["values"])
            if sheet == "UNIT_MASTER" and raw.get("uid") == cfg["unit_placeholder"]:
                raw.update(uid=branch.unit_id, name=branch.name, city=branch.city or None, status=branch.status)
            objs.append(model(branch=branch, row_no=r["row"], **_typed(spec, raw)))
        model.objects.bulk_create(objs)
    now = timezone.localtime()
    batch = next_id(ImportLog, "batch", f"IMP-{branch.unit_id[len('UNIT-'):]}-{now:%Y%m%d}-", 2, branch)
    BranchSetting.objects.bulk_create([
        BranchSetting(branch=branch, key=s["key"], label=s["param"], note=s["note"], row_no=s["row"],
                      **BranchSetting.split_value(batch if s["key"] == "batch" else s["value"]))
        for s in cfg["settings"]])
    ImportLog.objects.create(
        branch=branch, row_no=next_row_no(ImportLog, branch), batch=batch, date=now.strftime("%Y-%m-%d %H:%M"),
        file=cfg["source"]["workbook"], path="branches/template_config.json", sha=cfg["source"]["sha256"],
        sheets=", ".join([*cfg["tables"], "SETTINGS"]), rows="; ".join(f"{sheet} {len(rows)}" for sheet, rows in cfg["tables"].items()),
        excluded="data operasional (cabang baru)", ver=IMPORT_VERSION, notes="cabang baru dari template: identitas + konfigurasi SPI")
    audit.log(branch=branch, user=user, action="CREATE", entity="CABANG", entity_id=branch.code,
              new=f"{batch} · cabang baru dari template ({branch.name})")
    return branch
```

- [ ] **Step 5: Halaman Cabang**

Modify `core/decorators.py` — tambahkan di akhir:
```python
def require_super_admin(view):
    """Halaman semua cabang (SUPER_ADMIN): tidak memerlukan cabang aktif, jadi cabang pertama pun bisa dibuat."""
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_super_admin:
            return render(request, "core/forbidden.html", status=403)
        return view(request, *args, **kwargs)
    return wrapped
```

Modify `core/nav.py` — di awal `nav_for`, ganti baris `caps = getattr(request, "caps", frozenset())` dengan:
```python
    caps = getattr(request, "caps", frozenset())
    if getattr(getattr(request, "user", None), "is_super_admin", False):
        caps = caps | {Cap.MANAGE_ALL}                # menu semua cabang juga tampil tanpa cabang aktif
```

Modify `core/templates/core/no_access.html` — isi baru:
```html
{% extends "base.html" %}
{% block title %}Belum ada akses{% endblock %}
{% block content %}
<div class="mx-auto max-w-lg card p-6 text-center">
  {% if reason == "role" %}
    <h1 class="text-lg font-semibold">Belum ada halaman untuk peran Anda</h1>
    <p class="mt-2 text-sm text-slate-500">Peran Anda di {{ current_branch.name }} belum punya halaman di aplikasi ini.</p>
  {% elif user.is_super_admin %}
    <h1 class="text-lg font-semibold">Belum ada cabang</h1>
    <p class="mt-2 text-sm text-slate-500">Buat cabang pertama dari template, atau migrasikan workbook v4 cabang dengan perintah import_workbook (README).</p>
    <a href="{% url 'branches:list' %}" class="btn btn-primary mt-4">Buat cabang pertama</a>
  {% else %}
    <h1 class="text-lg font-semibold">Akun Anda belum punya akses cabang</h1>
    <p class="mt-2 text-sm text-slate-500">Minta Branch Admin cabang Anda memberi peran untuk email <strong>{{ user.email }}</strong>.</p>
  {% endif %}
</div>
{% endblock %}
```

`branches/forms.py`:
```python
import re

from django import forms

from .models import Branch

CODE_RE = re.compile(r"^SPI-[A-Z0-9]{2,12}$")


class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ["code", "name", "city", "address", "status", "language", "currency", "opening_date"]
        widgets = {"address": forms.Textarea(attrs={"rows": 2}),
                   "opening_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        if not CODE_RE.match(code):
            raise forms.ValidationError("Format Branch ID: SPI- lalu 2-12 huruf/angka, mis. SPI-AS.")
        if Branch.objects.filter(code__iexact=code).exists():
            raise forms.ValidationError("Branch ID ini sudah dipakai.")
        return code
```

`branches/views.py`:
```python
from django.contrib import messages
from django.db.models import Count
from django.shortcuts import redirect, render

from core.decorators import require_super_admin

from .forms import BranchForm
from .models import Branch
from .services import create_branch


@require_super_admin
def list_view(request):
    form = BranchForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        branch = create_branch(**form.cleaned_data, user=request.user)
        messages.success(request, f"Cabang {branch.name} ({branch.code}) dibuat: konfigurasi SPI dari template, tanpa data operasional.")
        return redirect("branches:list")
    branches = Branch.objects.annotate(n_users=Count("memberships")).order_by("code")
    return render(request, "branches/list.html", {"form": form, "branches": branches})
```

`branches/urls.py`:
```python
from django.urls import path

from . import views

app_name = "branches"
urlpatterns = [
    path("", views.list_view, name="list"),
]
```

Modify `spi_web/urls.py` — tambahkan ke `urlpatterns`:
```python
    path("cabang/", include("branches.urls")),
```

`branches/templates/branches/list.html`:
```html
{% extends "base.html" %}
{% block title %}Cabang{% endblock %}
{% block content %}
<h1 class="mb-6 text-2xl font-semibold text-slate-900">Cabang</h1>
<div class="grid gap-6 lg:grid-cols-3">
  <div class="card overflow-hidden lg:col-span-2">
    <table class="min-w-full divide-y divide-slate-200 text-sm">
      <thead class="bg-slate-50 text-left text-xs font-semibold uppercase text-slate-500">
        <tr><th class="px-4 py-3">Branch ID</th><th class="px-4 py-3">Nama</th><th class="px-4 py-3">Kota</th><th class="px-4 py-3">Unit</th>
          <th class="px-4 py-3">Status</th><th class="px-4 py-3 text-right">Pengguna</th></tr></thead>
      <tbody class="divide-y divide-slate-100">
        {% for b in branches %}
          <tr><td class="px-4 py-3 font-mono text-xs">{{ b.code }}</td><td class="px-4 py-3 font-medium">{{ b.name }}</td>
            <td class="px-4 py-3 text-slate-600">{{ b.city|default:"-" }}</td><td class="px-4 py-3 font-mono text-xs">{{ b.unit_id }}</td>
            <td class="px-4 py-3"><span class="badge {% if b.status == 'ACTIVE' %}bg-emerald-50 text-emerald-700{% elif b.status == 'NEW_BRANCH' %}bg-brand-50 text-brand-700{% else %}bg-slate-100 text-slate-600{% endif %}">{{ b.status }}</span></td>
            <td class="px-4 py-3 text-right tabular-nums">{{ b.n_users }}</td></tr>
        {% empty %}<tr><td colspan="6" class="px-4 py-6 text-center text-slate-500">Belum ada cabang.</td></tr>{% endfor %}
      </tbody>
    </table>
  </div>
  <form method="post" class="card form space-y-4 p-5">{% csrf_token %}
    <h2 class="font-semibold">Buat cabang baru</h2>
    <p class="text-xs text-slate-500">Konfigurasi SPI (program & level, kategori OFF, kunci tarif fee, parameter) disalin dari template cabang.
      Tabel murid, kelas, dan keuangan kosong. Cabang yang sudah punya workbook v4 (Jakarta, Alam Sutera) dimigrasi dengan perintah
      import_workbook --create (README) agar semua ID Excel, termasuk Log ID, tetap sama.</p>
    {% for field in form %}<div>{{ field.label_tag }}{{ field }}{% if field.help_text %}<span class="helptext">{{ field.help_text }}</span>{% endif %}{{ field.errors }}</div>{% endfor %}
    <button class="btn btn-primary w-full">Buat cabang</button>
  </form>
</div>
{% endblock %}
```

Run: `npm run build:css`

- [ ] **Step 6: Jalankan uji**

Run: `.venv/Scripts/python -m pytest`
Expected: semua lulus (termasuk 2 uji buat cabang + 3 uji halaman Cabang).

Run: `.venv/Scripts/python -m pytest -m slow branches`
Expected: `2 passed` — cabang baru web sama persis dengan hasil impor `SPI_ALAM_SUTERA_v4.xlsm` (identitas, 34 tabel, parameter).

- [ ] **Step 7: Commit**

```bash
git add tools/export_template_config.py branches core spi_web/urls.py static/css/app.css
git commit -m "feat: cabang baru dari template - konfigurasi SPI tanpa data operasional, setara workbook cabang Excel" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Verifikasi akhir — migrasi uji Jakarta & Alam Sutera, cek di browser, README

**Files:**
- Create: `README.md`, `.claude/launch.json` (tidak di-commit)
- Modify: `.gitignore` (tambah `.claude/` dan `.verify/`), `..\00_SYSTEM\CHANGE_LOG\CHANGE_LOG.md` (satu baris dokumentasi; bukan file APP)

- [ ] **Step 1: Semua uji**

Run:
```bash
.venv/Scripts/python -m pytest
.venv/Scripts/python -m pytest -m slow
```
Expected: semua uji cepat lulus; uji lambat `6 passed` (4 importer + 2 cabang).

- [ ] **Step 2: Migrasi uji ke database lokal (data asli, APP hanya dibaca)**

```bash
mkdir -p .verify && sha256sum ../APP/*.xlsm > .verify/app_sha_before.txt
.venv/Scripts/python scripts/devdb.py start
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py import_workbook "../APP/SPI_STUDENT-SPP_APP_2026_09_v4.xlsm" --branch SPI-JKT --create --name "SPI Jakarta" --city Jakarta --status ACTIVE
```
Expected (pratinjau): `Error 0 · peringatan 0` dan `Pratinjau saja - tidak ada yang disimpan.`

```bash
.venv/Scripts/python manage.py import_workbook "../APP/SPI_STUDENT-SPP_APP_2026_09_v4.xlsm" --branch SPI-JKT --create --name "SPI Jakarta" --city Jakarta --status ACTIVE --commit
.venv/Scripts/python manage.py import_workbook "../APP/SPI_ALAM_SUTERA_v4.xlsm" --branch SPI-AS --create --commit
.venv/Scripts/python manage.py import_workbook "../APP/SPI_STUDENT-SPP_APP_2026_09_v4.xlsm" --branch SPI-AS
```
Expected: `Tersimpan ke SPI-JKT: 15391 baris.`, `Tersimpan ke SPI-AS: 77 baris.`, lalu perintah ketiga gagal dengan `ERROR ... Workbook ini milik unit UNIT-JKT, bukan UNIT-AS` dan `Workbook punya error - tidak ada yang disimpan.`

Pengguna uji lokal (kata sandi acak, disimpan hanya di `.env` yang tidak di-commit):
```bash
.venv/Scripts/python - <<'EOF'
import os, pathlib, secrets
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spi_web.settings")
django.setup()
from accounts.models import User
env = pathlib.Path(".env")
text = env.read_text(encoding="utf-8")
if "DEV_SUPERUSER_PASSWORD=" not in text:
    text = text.rstrip("\n") + f"\nDEV_SUPERUSER_EMAIL=admin@spi.local\nDEV_SUPERUSER_PASSWORD={secrets.token_urlsafe(12)}\n" \
           f"DEV_CSO_EMAIL=cso.uji@spi.local\nDEV_CSO_PASSWORD={secrets.token_urlsafe(12)}\n"
    env.write_text(text, encoding="utf-8")
values = dict(line.split("=", 1) for line in text.splitlines() if "=" in line and not line.startswith("#"))
if not User.objects.filter(email=values["DEV_SUPERUSER_EMAIL"]).exists():
    User.objects.create_superuser(values["DEV_SUPERUSER_EMAIL"], values["DEV_SUPERUSER_PASSWORD"], full_name="Admin SPI (dev)")
print("pengguna uji dev siap:", values["DEV_SUPERUSER_EMAIL"], values["DEV_CSO_EMAIL"], "(kata sandi di .env)")
EOF
```

- [ ] **Step 3: Cek di browser**

`.claude/launch.json`:
```json
{
  "version": "0.0.1",
  "configurations": [
    {"name": "spi-web", "runtimeExecutable": ".venv/Scripts/python", "runtimeArgs": ["manage.py", "runserver", "127.0.0.1:8000"], "port": 8000}
  ]
}
```
Tambahkan baris `.claude/` dan `.verify/` ke `.gitignore`. Jalankan server (`preview_start` nama `spi-web`), lalu periksa:

1. Masuk sebagai `DEV_SUPERUSER_EMAIL` → halaman "Pilih cabang" berisi SPI Alam Sutera dan SPI Jakarta.
2. SPI Jakarta → Beranda (status ACTIVE): Murid 324 · Orang tua 172 · Riwayat bulanan 5488 · Kejadian Off 152 · Kelas 227 · Anggota kelas 449 · Slot jadwal 116 · Guru 25 · Program & level 16 · Baris buku kas 3898 · Pengeluaran 1398 · Periode 33 · Tagihan SPP 0 · Issue data 618 · Audit log 14.
3. Ganti ke SPI Alam Sutera lewat pemilih cabang → Program & level 16, Audit log 2, Murid 0, status ACTIVE (dari SETTINGS workbook); judul halaman memuat "SPI Alam Sutera".
4. Impor Data (SPI Alam Sutera aktif): unggah `SPI_STUDENT-SPP_APP_2026_09_v4.xlsm` → pratinjau berstatus "Ada error", temuan "bukan UNIT-AS", tanpa tombol simpan. Unggah `SPI_ALAM_SUTERA_v4.xlsm` → peringatan "sudah berisi data" + kotak centang; simpan tanpa centang → pesan error; centang lalu simpan → "Tersimpan"; Beranda: angka sama, Audit log 3 (hanya baris IMPORT baru; riwayat workbook tidak berlipat).
5. Cabang: dua cabang tercantum; buat `SPI-UJI` "SPI Uji" → muncul di daftar dan di pemilih cabang; Beranda SPI Uji: Program & level 16, Murid 0, Audit log 1.
6. Keluar → Daftar dengan `DEV_CSO_EMAIL` dan `DEV_CSO_PASSWORD` → "Cek email Anda"; buka tautan verifikasi dari log server (backend email konsol) → masuk → "Akun Anda belum punya akses cabang".
7. Masuk lagi sebagai super admin, SPI Jakarta → Pengguna & Akses → email CSO muncul di "Menunggu akses" → beri peran CSO → baris ACCESS tercatat (Audit log 15 di Beranda).
8. Masuk sebagai CSO → langsung SPI Jakarta (satu cabang); menu tanpa grup Admin; buka `/impor/` dan `/cabang/` → "Tidak diizinkan".
9. Lebar 375 px (`resize_window` preset mobile): menu samping tersembunyi di balik tombol menu, tabel bisa digeser, tidak ada gulir horizontal halaman. Kembalikan ke preset desktop.
10. `read_console_messages` tanpa error JavaScript.

Hentikan server dan database: `.venv/Scripts/python scripts/devdb.py stop`

```bash
sha256sum ../APP/*.xlsm | diff .verify/app_sha_before.txt - && echo "APP tidak berubah"
```
Expected: `APP tidak berubah` (Jakarta v4 `9d538012…092b9`, Alam Sutera `8dc4ba0a…291ef7`, Template `6ff4b6bf…f8ee00`).

- [ ] **Step 4: README**

`README.md`:
````markdown
# SPI Management — aplikasi web

Aplikasi web SPI yang mengikuti aplikasi Excel v4 (`..\APP\*.xlsm`): tabel, ID, aturan, dan alur yang sama, dengan antarmuka web.
Spesifikasi: `docs/superpowers/specs/2026-09-30-spi-web-design.md` · rencana: `docs/superpowers/plans/`.

## Status

Tahap 1A (fondasi) selesai: 34 tabel Excel v4 sebagai model per cabang (kolom rumus tidak disimpan), login dengan verifikasi email,
lupa/reset password, peran per cabang dan isolasi data cabang, penomoran ID & AUDIT_LOG seperti VBA, impor workbook v4
(pratinjau → simpan), dan cabang baru dari template. Berikutnya: tahap 1B (perhitungan + HOME / MURID / PROFIL setara Excel),
tahap 2 (operasional: form, SPP, kelas, akademik, OFF), tahap 3 (manajemen, admin, deploy).

## Menyiapkan (Windows, Git Bash, dari folder `app web`)

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
npm install && npm run vendor && npm run build:css
cp .env.example .env            # lalu isi SECRET_KEY acak (lihat rencana Task 1)
.venv/Scripts/python scripts/devdb.py start      # PostgreSQL lokal (pgserver), menulis DATABASE_URL ke .env
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py createcachetable
.venv/Scripts/python manage.py runserver
```

Super admin pertama: `.venv/Scripts/python manage.py createsuperuser`. Email dikirim ke konsol server selama `EMAIL_BACKEND` konsol.

## Migrasi data dari Excel

Workbook di `..\APP` hanya dibaca. Tanpa `--commit` perintah hanya menampilkan pratinjau (jumlah baris, error, peringatan).

```bash
.venv/Scripts/python manage.py import_workbook "../APP/SPI_STUDENT-SPP_APP_2026_09_v4.xlsm" --branch SPI-JKT --create --name "SPI Jakarta" --city Jakarta --status ACTIVE --commit
.venv/Scripts/python manage.py import_workbook "../APP/SPI_ALAM_SUTERA_v4.xlsm" --branch SPI-AS --create --commit
```

- Migrasi awal cabang yang sudah punya workbook: pakai perintah ini dengan `--create`, supaya semua ID Excel (termasuk Log ID) tetap sama.
- Impor ke cabang yang sudah berisi data hanya dengan `--replace` (di web: centang "ganti semua data cabang"). Isi tabel diganti;
  AUDIT_LOG dan IMPORT_LOG tidak pernah dihapus, dan baris riwayat yang sama tidak ditambahkan dua kali.
- Workbook cabang lain (Unit / Branch ID berbeda), workbook v1–v3, atau file bukan Excel ditolak.
- Cabang baru tanpa workbook: menu Admin → Cabang (super admin). Konfigurasi SPI disalin dari `branches/template_config.json`
  (hasil `tools/export_template_config.py` dari `SPI_BRANCH_TEMPLATE_v4.xlsm`).

## Uji

```bash
.venv/Scripts/python -m pytest              # uji cepat
.venv/Scripts/python -m pytest -m slow      # memakai workbook asli di ..\APP: jumlah baris & setiap sel Jakarta, Alam Sutera, template
```

## Alat pengembang (jalankan ulang hanya bila pipeline Excel berubah)

- `tools/export_schema.py` → `importer/schema/excel_tables.json` (definisi tabel dari `v2_layout.py`)
- `tools/generate_models.py` → `<app>/models_excel.py` (DIBANGKITKAN; lalu `makemigrations`)
- `tools/export_template_config.py` → `branches/template_config.json`

## Aturan yang dijaga

- Satu baris data = satu cabang; setiap halaman cabang mengecek peran di server.
- ID sama dengan Excel dan dibuat dalam transaksi dengan kunci cabang (tidak pernah ganda / dipakai ulang).
- Kontak tidak pernah ikut ekspor CSV (K2); tarif fee guru tidak dikarang (K3).
````

- [ ] **Step 5: Catatan perubahan proyek**

```bash
.venv/Scripts/python - <<'EOF'
import datetime, pathlib
p = pathlib.Path("../00_SYSTEM/CHANGE_LOG/CHANGE_LOG.md")
text = p.read_bytes().decode("utf-8")
row = ("| 52 | " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M") + " | Web tahap 1A | "
       r"Aplikasi web SPI (Django 5.2 + PostgreSQL) tahap 1A di `app web\`: 34 tabel Excel v4 sebagai model per cabang, login & verifikasi "
       r"email, peran & isolasi cabang, penomoran ID & AUDIT_LOG seperti VBA, impor workbook v4 (pratinjau → simpan; riwayat audit tidak "
       r"pernah hilang), cabang baru dari template. Migrasi uji ke database lokal: Jakarta 15.391 baris, Alam Sutera 77 baris; uji cepat & "
       r"lambat lulus | `app web\` (repo git sendiri) | Django, pytest; workbook `APP\` hanya dibaca | none (SHA-256 ketiga workbook "
       r"`APP\` sama sebelum & sesudah) | yes (hapus `app web\`) |")
anchor = "\r\n\r\nNotes\r\n"
assert text.count(anchor) == 1 and "| 52 |" not in text and "\x07" not in row
p.write_bytes(text.replace(anchor, "\r\n" + row + anchor).encode("utf-8"))
print("CHANGE_LOG baris 52 ditambahkan")
EOF
```

- [ ] **Step 6: Commit**

```bash
git add README.md .gitignore
git commit -m "docs: README tahap 1A - menyiapkan, migrasi dari Excel, uji" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
