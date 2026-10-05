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
# uang pada tabel transaksi: Decimal (docs/ARCHITECTURE.md A3)
MONEY_FIELDS = {("SPP_TAGIHAN", "harga"), ("SPP_TAGIHAN", "diskon"), ("SPP_TAGIHAN", "adj"), ("BUKTI_BAYAR", "nominal"),
                ("STUDENT_MASTER", "harga"), ("STUDENT_MASTER", "harga_in")}
MONEY = "models.DecimalField({v}, max_digits=14, decimal_places=2, null=True, blank=True{x})"
# kolom milik aplikasi (tidak ada di workbook, tidak diimpor) - docs/ARCHITECTURE.md A3
APP_FIELDS = {
    "PARENT_MASTER": [
        'kontak_darurat = models.CharField("Kontak darurat (nama)", max_length=150, blank=True, default="")',
        'telp_darurat = models.CharField("Telepon darurat", max_length=40, blank=True, default="")',
    ],
    "FOLLOW_UP": [
        'prioritas = models.CharField("Prioritas", max_length=12, blank=True, default="NORMAL")',
        'ditugaskan = models.ForeignKey("accounts.User", verbose_name="Ditugaskan ke", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")',
        'selesai_pada = models.DateTimeField("Selesai pada", null=True, blank=True)',
        'diubah_pada = models.DateTimeField("Diubah pada", auto_now=True, null=True)',
    ],
}


def field_line(f, is_key, sheet):
    v = repr(f["header"])
    if is_key and f["kind"] == "text":
        return f'    {f["name"]} = models.CharField({v}, max_length=200, db_index=True)'
    x = ", db_index=True" if (is_key or f["header"] in INDEXED) else ""
    kind = MONEY if (sheet, f["name"]) in MONEY_FIELDS else FIELD[f["kind"]]
    return f'    {f["name"]} = ' + kind.format(v=v, x=x)


def model_block(t):
    lines = [f'class {t["model"]}(ExcelRow):', f'    EXCEL_SHEET = {t["sheet"]!r}', f'    EXCEL_KEY = {t["key"]!r}', ""]
    for f in t["fields"]:
        if not f["stored"]:
            continue
        lines.append(field_line(f, f["name"] == t["key"], t["sheet"]))
        if f["text_field"]:
            lines.append(f'    {f["text_field"]} = models.TextField({(f["header"] + " (teks asli)")!r}, blank=True, default="")')
    if t["sheet"] in APP_FIELDS:
        lines += ["    # kolom aplikasi (tidak diimpor dari workbook)"] + [f"    {line}" for line in APP_FIELDS[t["sheet"]]]
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
