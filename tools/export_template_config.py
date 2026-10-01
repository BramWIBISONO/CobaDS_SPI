"""Ekspor konfigurasi SPI dari SPI_BRANCH_TEMPLATE_v4.xlsm ke branches/template_config.json (alat pengembang, hanya membaca workbook).
Isi = tabel yang tidak kosong di template (program & level, kategori OFF, unit, kunci tarif fee) + parameter SETTINGS yang disimpan per
cabang (aturan importer.commit.stored_settings). Template tidak berisi data operasional.
    .venv/Scripts/python tools/export_template_config.py"""
import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WEB))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spi_web.settings")
import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402

from importer.commit import LOG_TABLES, stored_settings  # noqa: E402
from importer.reader import read_workbook  # noqa: E402

SOURCE = settings.SPI_EXCEL_DIR / "SPI_BRANCH_TEMPLATE_v4.xlsm"
OUT = WEB / "branches" / "template_config.json"
UNIT_PLACEHOLDER = "UNIT-XXX"


def plain(value, where):
    if isinstance(value, (datetime.date, datetime.time)):
        raise SystemExit(f"{where}: nilai tanggal/jam belum didukung template_config.json - tambahkan penanganannya dulu")
    return value


def main():
    data = read_workbook(SOURCE)
    tables = {sheet: [{"row": r.row, "values": {k: plain(v, f"{sheet} baris {r.row}") for k, v in r.values.items()}} for r in rows]
              for sheet, rows in data.tables.items() if rows and sheet not in LOG_TABLES}
    assert UNIT_PLACEHOLDER in [r["values"]["uid"] for r in tables["UNIT_MASTER"]], "baris unit template tidak ditemukan"
    rows = [{"key": s["key"], "param": s["param"], "value": plain(s["value"], f"SETTINGS {s['key']}"), "note": s["note"], "row": s["row"]}
            for s in stored_settings(data.settings)]
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    OUT.write_text(json.dumps({"source": {"workbook": SOURCE.name, "sha256": digest}, "unit_placeholder": UNIT_PLACEHOLDER,
                               "tables": tables, "settings": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("tabel", {sheet: len(r) for sheet, r in tables.items()}, "| parameter", len(rows), "| sha256", digest[:12])


if __name__ == "__main__":
    main()
