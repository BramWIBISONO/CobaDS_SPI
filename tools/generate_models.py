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
