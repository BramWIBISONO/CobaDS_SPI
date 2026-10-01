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
