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
