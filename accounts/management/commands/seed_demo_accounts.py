"""Buat / perbarui akun demo per peran (hanya DEBUG & DEMO_ACCOUNTS). Kata sandi: DEMO_PASSWORD di .env.
    .venv/Scripts/python manage.py seed_demo_accounts"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.demo import demo_enabled, ensure_password, seed


class Command(BaseCommand):
    help = "Akun demo per peran untuk mencoba aplikasi di laptop."

    def handle(self, *args, **opts):
        if not demo_enabled():
            raise CommandError("Akun demo hanya untuk laptop: set DEBUG=True dan DEMO_ACCOUNTS=True di .env.")
        for row in seed(ensure_password(settings.ENV_FILE)):
            self.stdout.write(f"  {row['email']:28} {row['role']:13} {row['branch'] or 'semua cabang':10} {row['status']}")
        self.stdout.write(self.style.SUCCESS("Selesai. Kata sandi bersama: lihat DEMO_PASSWORD di file .env (tidak ditampilkan)."))
