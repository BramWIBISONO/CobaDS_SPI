import datetime

import pytest

from branches.models import Branch
from importer.reader import WorkbookError, read_workbook
from importer.tests.factories import build_workbook
from importer.validate import validate

STUDENTS = [
    {"Student ID": "STD-000001", "Nama Murid": "Ani", "Parent ID": "PAR-00001", "Harga SPP": 450000, "Tanggal Lahir": datetime.datetime(2016, 5, 10)},
    {"Student ID": "STD-000002", "Nama Murid": "Budi", "Parent ID": "PAR-00009", "Harga SPP": "gratis"},
]
PARENTS = [{"Parent ID": "PAR-00001", "Nama Orang Tua": "Ibu Ani"}]


def errors(issues):
    return [i for i in issues if i.level == "error"]


def test_valid_workbook_reads_rows_by_header(tmp_path):
    path = build_workbook(tmp_path / "ok.xlsx", {"STUDENT_MASTER": STUDENTS, "PARENT_MASTER": PARENTS})
    data = read_workbook(path)
    assert [r.values["std"] for r in data.tables["STUDENT_MASTER"]] == ["STD-000001", "STD-000002"]
    assert data.tables["STUDENT_MASTER"][0].row == 6
    assert data.unit == "UNIT-JKT"
    issues = validate(data, Branch(code="SPI-JKT", name="SPI Jakarta"))
    assert errors(issues) == []
    assert [i.message for i in issues if i.level == "warning"] == ["'PAR-00009' tidak ada di PARENT_MASTER (Parent ID)."]


def test_file_that_is_not_excel_is_refused(tmp_path):
    path = tmp_path / "catatan.xlsx"
    path.write_text("bukan excel", encoding="utf-8")
    with pytest.raises(WorkbookError, match="bukan workbook Excel"):
        read_workbook(path)


def test_workbook_without_v4_sheets_is_refused(tmp_path):
    path = build_workbook(tmp_path / "v3.xlsx", drop_sheets=("SPP_TAGIHAN", "SESI"))
    with pytest.raises(WorkbookError, match="Bukan workbook SPI v4"):
        read_workbook(path)


def test_missing_column_is_an_error(tmp_path):
    path = build_workbook(tmp_path / "x.xlsx", rename_headers={("STUDENT_MASTER", "Nama Murid"): "Nama"})
    issues = validate(read_workbook(path))
    assert any(i.level == "error" and i.field == "Nama Murid" for i in issues)


def test_duplicate_ids_and_bad_values_are_errors(tmp_path):
    rows = {"STUDENT_MASTER": [STUDENTS[0], dict(STUDENTS[0])], "PARENT_MASTER": PARENTS,
            "SPP_TAGIHAN": [{"Tagihan ID": "TAG-202610-STD-000001", "Student ID": "STD-000001", "Harga SPP": "banyak"}]}
    messages = [i.message for i in errors(validate(read_workbook(build_workbook(tmp_path / "x.xlsx", rows))))]
    assert any("ID ganda 'STD-000001'" in m for m in messages)
    assert any("bukan angka" in m for m in messages)


def test_bill_for_unknown_student_is_an_error(tmp_path):
    rows = {"SPP_TAGIHAN": [{"Tagihan ID": "TAG-202610-STD-000404", "Student ID": "STD-000404", "Harga SPP": 450000}]}
    issues = errors(validate(read_workbook(build_workbook(tmp_path / "x.xlsx", rows))))
    assert [(i.table, i.field) for i in issues] == [("SPP_TAGIHAN", "Student ID")]


def test_twin_students_are_a_warning(tmp_path):
    twin = dict(STUDENTS[0], **{"Student ID": "STD-000003"})
    issues = validate(read_workbook(build_workbook(tmp_path / "x.xlsx", {"STUDENT_MASTER": [STUDENTS[0], twin], "PARENT_MASTER": PARENTS})))
    assert any(i.level == "warning" and "tanggal lahir sama" in i.message for i in issues)


def test_workbook_of_another_branch_is_an_error(tmp_path):
    data = read_workbook(build_workbook(tmp_path / "x.xlsx", settings={"unit": "UNIT-JKT"}))
    issues = errors(validate(data, Branch(code="SPI-AS", name="SPI Alam Sutera")))
    assert issues and "bukan UNIT-AS" in issues[0].message
    data = read_workbook(build_workbook(tmp_path / "y.xlsx", settings={"branch_id": "SPI-AS", "unit": "UNIT-AS"}))
    assert any("milik cabang SPI-AS" in i.message for i in errors(validate(data, Branch(code="SPI-JKT", name="SPI Jakarta"))))


def test_simulation_block_keeps_filled_rows_and_ends_at_the_first_blank_row(tmp_path):
    rows = {"SIMULASI_JADWAL": [{"No Simulasi": "SIM-01"}, {"No Simulasi": "SIM-02", "Murid": "Ani", "Hari": "SENIN"}, {},
                                {"No Simulasi": "Jam", "Murid": "Guru", "Jam Mulai": "Guru ▸"}]}   # tampilan JADWAL RESMI
    data = read_workbook(build_workbook(tmp_path / "x.xlsx", rows))
    assert [(r.row, r.values["no"], r.values["murid"]) for r in data.tables["SIMULASI_JADWAL"]] == [(7, "SIM-02", "Ani")]
    assert errors(validate(data)) == []
