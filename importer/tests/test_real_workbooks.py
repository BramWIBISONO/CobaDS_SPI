"""Workbook asli di ..\\APP (hanya dibaca). Jalankan: .venv/Scripts/python -m pytest -m slow importer/tests/test_real_workbooks.py"""
import pytest
from django.conf import settings

from branches.models import Branch, BranchSetting
from importer.commit import commit_workbook
from importer.convert import convert
from importer.reader import WorkbookError, read_workbook
from importer.schema import load_schema
from importer.validate import validate

pytestmark = pytest.mark.slow
JKT = settings.SPI_EXCEL_DIR / "SPI_STUDENT-SPP_APP_2026_09_v4.xlsm"
AS = settings.SPI_EXCEL_DIR / "SPI_ALAM_SUTERA_v4.xlsm"
V3 = settings.SPI_EXCEL_DIR / "SPI_STUDENT-SPP_APP_2026_09_v3.xlsm"
JKT_COUNTS = {
    "STUDENT_MASTER": 324, "STUDENT_ID_MAPPING": 1448, "STUDENT_OFF": 152, "OFF_REASON_MASTER": 86, "CLASS_MASTER": 227,
    "CLASS_MEMBERS": 449, "CLASS_SCHEDULE": 116, "TEACHER_MASTER": 25, "PROGRAM_MASTER": 16, "PARTNER_MASTER": 126,
    "ROOM_MASTER": 8, "UNIT_MASTER": 11, "ISSUE_UNIT": 618, "BUKU_KAS": 3898, "PEMBAYAR": 172, "NOTA_LOG": 0, "SIMULASI_JADWAL": 0,
    "PERIODE": 33, "STATUS_EVENT": 0, "PARENT_MASTER": 172, "SPP_TAGIHAN": 0, "BUKTI_BAYAR": 0, "SESI": 0, "TARIF_FEE": 40,
    "FOLLOW_UP": 1, "ACADEMIC_RECORD": 0, "LEAD": 0, "DOKUMEN": 0, "BUKU_KAS_KELUAR": 1398, "IMPORT_LOG": 228,
    "SOURCE_REFERENCE": 18, "AUDIT_LOG": 13, "D_BULAN": 5488, "D_MURID": 324,
}


@pytest.fixture(scope="module")
def jkt_data():
    return read_workbook(JKT)


@pytest.mark.django_db
def test_jakarta_imports_without_errors_and_every_cell_is_kept(jkt_data):
    branch = Branch.objects.create(code="SPI-JKT", name="SPI Jakarta", city="Jakarta", status="ACTIVE")
    assert [i for i in validate(jkt_data, branch) if i.level == "error"] == []
    counts = commit_workbook(jkt_data, branch, None, replace=False, file_name=JKT.name, sha256="-")
    assert counts == JKT_COUNTS
    for spec in load_schema():
        rows = {o.row_no: o for o in spec.model_class().objects.for_branch(branch)}
        for r in jkt_data.tables[spec.sheet]:
            obj = rows[r.row]
            for f in spec.stored_fields:
                for name, expected in convert(f, r.values[f.name]).items():
                    assert getattr(obj, name) == expected, (spec.sheet, r.row, f.header)
    kept = BranchSetting.objects.filter(branch=branch)
    assert kept.count() == 26 and not kept.filter(key__in=["unit", "periode", "hari_ini", "bulan_ini"]).exists()
    assert (kept.get(key="ambang").value, kept.get(key="nota_awalan").value) == (20000000.0, "SPI-JKT/SPP/")


@pytest.mark.django_db
def test_jakarta_workbook_cannot_go_into_alam_sutera(jkt_data):
    alam_sutera = Branch.objects.create(code="SPI-AS", name="SPI Alam Sutera", city="Tangerang", status="ACTIVE")
    assert any(i.level == "error" and "UNIT-JKT" in i.message for i in validate(jkt_data, alam_sutera))


@pytest.mark.django_db
def test_alam_sutera_imports_as_a_configured_branch_without_operational_data():
    branch = Branch.objects.create(code="SPI-AS", name="(sementara)", status="NEW_BRANCH")
    data = read_workbook(AS)
    assert [i for i in validate(data, branch) if i.level == "error"] == []
    counts = commit_workbook(data, branch, None, replace=False, file_name=AS.name, sha256="-")
    assert {s: n for s, n in counts.items() if n} == {"OFF_REASON_MASTER": 17, "PROGRAM_MASTER": 16, "UNIT_MASTER": 2,
                                                      "TARIF_FEE": 40, "IMPORT_LOG": 1, "AUDIT_LOG": 1}
    branch.refresh_from_db()
    assert (branch.name, branch.city, branch.status, branch.language, branch.currency) == (
        "SPI Alam Sutera", "Tangerang", "ACTIVE", "Indonesia", "IDR")
    kept = set(BranchSetting.objects.filter(branch=branch).values_list("key", flat=True))
    assert len(kept) == 23 and "ambang" in kept and not kept & {"nota_kop", "nota_awalan", "mulai_v4", "branch_name", "unit"}


def test_old_v3_workbook_is_refused():
    with pytest.raises(WorkbookError, match="Bukan workbook SPI v4"):
        read_workbook(V3)
