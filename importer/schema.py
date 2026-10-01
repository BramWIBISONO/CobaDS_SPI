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
