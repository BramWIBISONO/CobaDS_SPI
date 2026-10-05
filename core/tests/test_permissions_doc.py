from pathlib import Path

from django.conf import settings

from core.management.commands.permissions_doc import render_doc


def test_permission_document_matches_the_code():
    doc = (Path(settings.BASE_DIR) / "docs" / "PERMISSIONS.md").read_text(encoding="utf-8")
    assert doc == render_doc(), "jalankan: .venv/Scripts/python manage.py permissions_doc"
