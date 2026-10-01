import datetime
import re

import pytest

from audit.models import AuditLog, ImportLog
from branches.models import BranchSetting
from core import audit
from importer.commit import ImportBlocked, branch_has_data, commit_workbook
from importer.reader import read_workbook
from importer.tests.factories import build_workbook
from students.models import StudentMaster

ROWS = {
    "STUDENT_MASTER": [{"Student ID": "STD-000001", "Nama Murid": "Ani", "Harga SPP": 450000, "Join": datetime.datetime(2025, 1, 6)},
                       {"Student ID": "STD-000002", "Nama Murid": "Budi", "Harga SPP": "gratis", "Join": "Agustus 2024"}],
    "AUDIT_LOG": [{"Log ID": "LOG-000001", "Action": "CREATE", "Entity": "WORKBOOK", "Detected By": "SYSTEM",
                   "Timestamp": datetime.datetime(2026, 9, 30, 8, 53)}],
}
SETTINGS = {"unit": "UNIT-JKT", "off_lama": 3, "nota_kop": "SPI Jakarta", "mulai_v4": datetime.datetime(2026, 10, 1),
            "versi": "v2.0-fase1", "hari_ini": "=TODAY()"}


@pytest.fixture
def data(tmp_path):
    return read_workbook(build_workbook(tmp_path / "jkt.xlsx", ROWS, SETTINGS))


def commit(data, branch, replace=False):
    return commit_workbook(data, branch, None, replace=replace, file_name="jkt.xlsx", sha256="abc")


@pytest.mark.django_db
def test_commit_stores_rows_in_sheet_order_with_mixed_values(data, branch, make_user):
    counts = commit_workbook(data, branch, make_user("admin@spi.test"), replace=False, file_name="jkt.xlsx", sha256="abc")
    assert counts["STUDENT_MASTER"] == 2 and counts["AUDIT_LOG"] == 1
    ani, budi = StudentMaster.objects.for_branch(branch).order_by("row_no")
    assert (ani.row_no, ani.harga, ani.join) == (6, 450000.0, datetime.date(2025, 1, 6))
    assert (budi.harga, budi.harga_text, budi.join, budi.join_text) == (None, "gratis", None, "Agustus 2024")


@pytest.mark.django_db
def test_commit_keeps_settings_except_identity_and_formulas_and_logs_the_import(data, branch):
    commit(data, branch)
    keys = set(BranchSetting.objects.filter(branch=branch).values_list("key", flat=True))
    assert keys == {"off_lama", "nota_kop", "mulai_v4", "versi"}       # 'unit' dari Branch ID; 'hari_ini' rumus
    assert BranchSetting.objects.get(branch=branch, key="mulai_v4").value == datetime.date(2026, 10, 1)
    log = ImportLog.objects.for_branch(branch).get()
    assert re.fullmatch(r"IMP-JKT-\d{8}-01", log.batch) and log.sha == "abc" and log.file == "jkt.xlsx"
    imported, ours = AuditLog.objects.for_branch(branch).order_by("row_no")
    assert (imported.lid, imported.by, ours.lid, ours.action, ours.eid) == ("LOG-000001", "SYSTEM", "LOG-000002", "IMPORT", "jkt.xlsx")


@pytest.mark.django_db
def test_second_import_needs_replace_and_never_duplicates(data, branch):
    commit(data, branch)
    assert branch_has_data(branch)
    with pytest.raises(ImportBlocked):
        commit(data, branch)
    commit(data, branch, replace=True)
    assert StudentMaster.objects.for_branch(branch).count() == 2
    assert list(AuditLog.objects.for_branch(branch).order_by("row_no").values_list("lid", "action")) == [
        ("LOG-000001", "CREATE"), ("LOG-000002", "IMPORT"), ("LOG-000003", "IMPORT")]
    assert [b[-3:] for b in ImportLog.objects.for_branch(branch).order_by("row_no").values_list("batch", flat=True)] == ["-01", "-02"]


@pytest.mark.django_db
def test_audit_history_written_by_the_web_is_kept_and_never_renumbered(data, branch):
    audit.log(branch=branch, user=None, action="GRANT", entity="PENGGUNA", entity_id="cso@spi.test", new="CSO")
    assert not branch_has_data(branch)                                # riwayat saja bukan data cabang
    commit(data, branch)
    commit(data, branch, replace=True)
    assert list(AuditLog.objects.for_branch(branch).order_by("row_no").values_list("lid", "action")) == [
        ("LOG-000001", "GRANT"), ("LOG-000002", "CREATE"), ("LOG-000003", "IMPORT"), ("LOG-000004", "IMPORT")]
    assert "1 baris AUDIT_LOG" in ImportLog.objects.for_branch(branch).order_by("row_no").first().notes


@pytest.mark.django_db
def test_import_does_not_touch_other_branches(data, branch, other_branch):
    StudentMaster.objects.create(branch=other_branch, std="STD-000001", nama="Murid AS", row_no=6)
    commit(data, branch)
    assert StudentMaster.objects.for_branch(other_branch).get().nama == "Murid AS"


@pytest.mark.django_db
def test_identity_rows_update_the_branch_and_are_audited(tmp_path, other_branch):
    settings = {"branch_id": "SPI-AS", "branch_name": "SPI Alam Sutera", "branch_city": "Tangerang", "branch_status": "ACTIVE",
                "branch_open": None, "unit": "UNIT-AS"}
    data = read_workbook(build_workbook(tmp_path / "as.xlsx", {}, settings))
    other_branch.city, other_branch.status = "", "NEW_BRANCH"
    other_branch.save()
    commit_workbook(data, other_branch, None, replace=False, file_name="as.xlsx", sha256="x")
    other_branch.refresh_from_db()
    assert (other_branch.city, other_branch.status, other_branch.opening_date) == ("Tangerang", "ACTIVE", None)
    assert not BranchSetting.objects.filter(branch=other_branch).exists()
    changes = AuditLog.objects.for_branch(other_branch).filter(action="UPDATE").order_by("row_no")
    assert [(c.entity, c.field, c.old, c.new) for c in changes] == [("CABANG", "Kota", "", "Tangerang"),
                                                                   ("CABANG", "Status cabang", "NEW_BRANCH", "ACTIVE")]
