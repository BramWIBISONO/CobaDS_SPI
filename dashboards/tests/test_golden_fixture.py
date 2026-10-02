"""Fixture angka emas = nilai Excel yang diketahui (HOME & DASHBOARD Sep 2026) dan tidak memuat nama murid."""
import json
from pathlib import Path

GOLDEN = json.loads((Path(__file__).parent / "golden" / "jkt_golden.json").read_text(encoding="utf-8"))
DEFAULT = {"bulan": "Sep 2026", "program": "Semua", "tipe": "Semua", "mode": "Semua", "guru": "Semua"}


def test_fixture_holds_the_known_excel_numbers():
    h = GOLDEN["home"]
    assert (h["aktif"], h["spp"], h["off"], h["kelas"], h["kritis"]) == (154, 69051000, 118, 106, 2)
    sep = next(s for s in GOLDEN["laporan"] if s["filter"] == DEFAULT)
    assert sep["murid"] == [157, 154, 3, 0, 3, 36, 9]
    assert sep["spp"][:2] == [69051000, 765383125]
    assert GOLDEN["meta"]["hari_ini"] == "2026-09-30"
    assert len(GOLDEN["lists"]["bulan"]) == 33 and GOLDEN["lists"]["bulan"][-1] == "Sep 2026"


def test_fixture_has_no_student_names():
    text = json.dumps(GOLDEN, ensure_ascii=False)
    assert "Abygail" not in text and "Alberto Jayaharto" not in text
