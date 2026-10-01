import datetime

import pytest

from importer.convert import ConvertError, convert
from importer.schema import table

SM = table("STUDENT_MASTER").field_by_header


def test_text_keeps_the_value_and_whole_numbers_lose_the_decimal():
    assert convert(SM["Nama Murid"], "Abygail Greysel Chu") == {"nama": "Abygail Greysel Chu"}
    assert convert(SM["Nama Murid"], None) == {"nama": ""}
    assert convert(table("CLASS_MASTER").field_by_header["Kode Kelas"], 12.0)["code"] == "12"


def test_mixed_number_column_keeps_text_separately():
    assert convert(SM["Harga SPP"], 670000) == {"harga": 670000.0, "harga_text": ""}
    assert convert(SM["Harga SPP"], "Rp 500.000 (promo)") == {"harga": None, "harga_text": "Rp 500.000 (promo)"}


def test_mixed_date_column():
    assert convert(SM["Join"], datetime.datetime(2025, 12, 3)) == {"join": datetime.date(2025, 12, 3), "join_text": ""}
    assert convert(SM["Join"], "Agustus 2024") == {"join": None, "join_text": "Agustus 2024"}


def test_text_in_a_pure_number_column_is_an_error():
    with pytest.raises(ConvertError):
        convert(table("SPP_TAGIHAN").field_by_header["Harga SPP"], "lima ratus ribu")


def test_datetime_gets_the_jakarta_timezone():
    ts = convert(table("AUDIT_LOG").field_by_header["Timestamp"], datetime.datetime(2026, 9, 30, 8, 53))["ts"]
    assert ts.utcoffset() == datetime.timedelta(hours=7)


def test_time_from_a_day_fraction():
    mulai = table("SESI").field_by_header["Mulai"]
    assert convert(mulai, 0.375) == {"mulai": datetime.time(9, 0)}
    assert convert(mulai, datetime.time(15, 30)) == {"mulai": datetime.time(15, 30)}
