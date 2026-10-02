"""Kesamaan dengan Excel tanpa toleransi (angka emas golden/jkt_golden.json). Lambat - mengimpor workbook Jakarta asli:
    .venv/Scripts/python -m pytest -m slow dashboards"""
import datetime
import hashlib
import json
from pathlib import Path

import pytest
from django.conf import settings

from branches.models import Branch
from dashboards.calc.base import HIST_MONTHS, BranchData, fold, label
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


def scenario(f):
    from dashboards.calc.laporan import Filter
    bulan = {label(m): m for m in HIST_MONTHS}[f["bulan"]]
    return Filter(bulan, f["program"], f["tipe"], f["mode"], f["guru"])


@pytest.mark.parametrize("i", range(len(GOLDEN["laporan"])))
def test_laporan_murid(data, i):
    from dashboards.calc.laporan import ringkasan_murid
    gold = GOLDEN["laporan"][i]
    r = ringkasan_murid(data, scenario(gold["filter"]))
    web = {"murid": r["murid"], "status": [n for _l, n in r["status"]], "level": r["level"], "tipe": r["tipe"], "guru": r["guru"],
           "tren": r["tren"], "jumlah": [len(r["baru"]), len(r["off_baru"]), len(r["daftar"])]}
    want = {k: gold[k] for k in ("murid", "status", "level", "tipe", "guru", "tren")}
    want["jumlah"] = [gold["jumlah"][0], gold["jumlah"][1], gold["jumlah"][3]]
    assert_same(web, want, f"laporan {gold['filter']}")


def test_kas_rows(data):
    from dashboards.calc.kas import kas_rows
    web = {k.row.lid: [k.dihitung, *k.s, *k.b] for k in kas_rows(data) if k.row.lid}
    assert_same(web, GOLDEN["kas_rows"], "BUKU_KAS Dihitung / Student ID / Bagian")


def test_kas_bulanan(data):
    from dashboards.calc.kas import bulanan
    assert_same([[label(b), t, l, n] for b, t, l, n in bulanan(data)], GOLDEN["kas_bulanan"], "C_KAS per bulan")


@pytest.mark.parametrize("i", range(len(GOLDEN["laporan"])))
def test_laporan_spp(data, i):
    from dashboards.calc.kas import ringkasan_spp
    gold = GOLDEN["laporan"][i]
    r = ringkasan_spp(data, scenario(gold["filter"]))
    assert_same({"spp": r["spp"], "belum_bayar": len(r["belum_bayar"])}, {"spp": gold["spp"][:7], "belum_bayar": gold["jumlah"][2]},
                f"SPP {gold['filter']}")


@pytest.mark.parametrize("i", [i for i, s in enumerate(GOLDEN["laporan"]) if "baris" in s])
def test_laporan_rows(data, i):
    from dashboards.calc.kas import ringkasan_spp
    from dashboards.calc.laporan import baris_laporan
    gold = GOLDEN["laporan"][i]
    f = scenario(gold["filter"])
    per = ringkasan_spp(data, f)["per_baris"]
    web = {b.v1: [b.status, b.kelompok, int(b.ikut), int(b.off_baru), *per[id(b.murid)]] for b in baris_laporan(data, f)}
    assert_same(web, gold["baris"], f"baris {gold['filter']}")
