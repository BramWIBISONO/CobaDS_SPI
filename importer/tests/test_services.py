import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command

from branches.models import Branch
from importer.commit import ImportBlocked
from importer.services import commit_run, create_run, grouped_counts
from importer.tests.factories import build_workbook
from students.models import StudentMaster

STUDENTS = {"STUDENT_MASTER": [{"Student ID": "STD-000001", "Nama Murid": "Ani"}]}


def upload(tmp_path, name="jkt.xlsx", rows=STUDENTS, settings=None):
    path = build_workbook(tmp_path / name, rows, settings)
    return SimpleUploadedFile(name, path.read_bytes())


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.mark.django_db
def test_preview_stores_nothing_and_commit_saves_once(tmp_path, branch, make_user):
    user = make_user("admin@spi.test")
    run = create_run(upload(tmp_path), branch, user)
    assert run.status == "PREVIEW" and run.report["ok"] and run.report["counts"]["STUDENT_MASTER"] == 1
    assert len(run.sha256) == 64 and not StudentMaster.objects.exists()
    students = next(g for g in grouped_counts(run.report) if g["label"] == "Murid")
    assert {"sheet": "STUDENT_MASTER", "new": 1, "existing": 0, "saved": None} in students["tables"]
    assert commit_run(run, user, replace=False)["STUDENT_MASTER"] == 1
    run.refresh_from_db()
    assert run.status == "COMMITTED" and run.committed_by == user
    with pytest.raises(ImportBlocked, match="sudah diproses"):
        commit_run(run, user, replace=True)
    assert StudentMaster.objects.count() == 1


@pytest.mark.django_db
def test_workbook_with_errors_or_of_another_branch_cannot_be_committed(tmp_path, branch, make_user):
    user = make_user("admin@spi.test")
    run = create_run(upload(tmp_path, settings={"unit": "UNIT-AS"}), branch, user)
    assert not run.report["ok"] and run.report["errors"] == 1
    with pytest.raises(ImportBlocked):
        commit_run(run, user, replace=False)
    broken = SimpleUploadedFile("rusak.xlsx", b"bukan excel")
    run = create_run(broken, branch, user)
    assert not run.report["ok"] and "bukan workbook Excel" in run.report["fatal"]
    assert not StudentMaster.objects.exists()


@pytest.mark.django_db
def test_command_previews_by_default_and_can_create_the_branch(tmp_path):
    settings = {"branch_id": "SPI-AS", "branch_name": "SPI Alam Sutera", "branch_city": "Tangerang", "unit": "UNIT-AS"}
    path = build_workbook(tmp_path / "as.xlsx", STUDENTS, settings)
    with pytest.raises(CommandError, match="--create"):
        call_command("import_workbook", str(path), "--branch", "SPI-AS")
    call_command("import_workbook", str(path), "--branch", "SPI-AS", "--create")
    assert not Branch.objects.exists()                               # pratinjau: cabang pun tidak disimpan
    call_command("import_workbook", str(path), "--branch", "spi-as", "--create", "--commit")
    branch = Branch.objects.get(code="SPI-AS")
    assert (branch.name, branch.city) == ("SPI Alam Sutera", "Tangerang")
    assert StudentMaster.objects.for_branch(branch).count() == 1
    with pytest.raises(CommandError, match="sudah berisi data"):
        call_command("import_workbook", str(path), "--branch", "SPI-AS", "--commit")
