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
