"""Kesamaan dengan Excel tanpa toleransi (angka emas golden/jkt_golden.json). Lambat - mengimpor workbook Jakarta asli:
    .venv/Scripts/python -m pytest -m slow dashboards"""
import datetime
import hashlib
import json
from pathlib import Path

import pytest
from django.conf import settings

from branches.models import Branch
from dashboards.calc.base import BranchData, fold, label
from dashboards.calc.status import guru_dipakai, kode_dipakai, semua_status_sekarang
from importer.commit import commit_workbook
from importer.reader import read_workbook
from importer.schema import load_schema

pytestmark = pytest.mark.slow
GOLDEN = json.loads((Path(__file__).parent / "golden" / "jkt_golden.json").read_text(encoding="utf-8"))
TODAY = datetime.date.fromisoformat(GOLDEN["meta"]["hari_ini"])
SOURCE = settings.SPI_EXCEL_DIR / GOLDEN["meta"]["workbook"]


def norm(v):
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return [norm(x) for x in v]
    if isinstance(v, dict):
        return {k: norm(x) for k, x in v.items()}
    if isinstance(v, datetime.date):
        return v.isoformat()
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def assert_same(web, gold, what):
    web, gold = norm(web), norm(gold)
    if isinstance(gold, dict):
        missing, extra = sorted(set(gold) - set(web))[:10], sorted(set(web) - set(gold))[:10]
        diff = {k: (web[k], gold[k]) for k in gold if k in web and web[k] != gold[k]}
        assert (missing, extra, dict(list(diff.items())[:10])) == ([], [], {}), f"{what}: {len(diff)} beda"
    else:
        assert web == gold, what


@pytest.fixture(scope="module")
def jkt(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        branch = Branch.objects.create(code="SPI-JKT", name="SPI Jakarta", city="Jakarta", status="ACTIVE")
        commit_workbook(read_workbook(SOURCE), branch, None, replace=False, file_name=SOURCE.name, sha256="-")
    yield branch
    with django_db_blocker.unblock():
        for spec in load_schema():
            spec.model_class().objects.filter(branch=branch).delete()
        branch.delete()


@pytest.fixture
def data(jkt, db):
    return BranchData(jkt, TODAY)


def test_golden_numbers_belong_to_the_current_workbook():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == GOLDEN["meta"]["sha256"]


def test_lists(data):
    lists = GOLDEN["lists"]
    web = {"bulan": [label(m) for m in data.months_hist], "program": data.programs, "tipe": data.tipes, "mode": data.modes,
           "guru": data.gurus, "level": data.levels, "kas_bulan": [label(m) for m in data.kas_months]}
    assert_same(web, {k: lists[k] for k in web}, "daftar")


def test_students_now(data):
    st = semua_status_sekarang(data)
    web = {s.std: [st[fold(s.std)], kode_dipakai(s), guru_dipakai(s)] for s in data.students if s.std}
    assert_same(web, GOLDEN["students"], "status sekarang / kode / guru")
