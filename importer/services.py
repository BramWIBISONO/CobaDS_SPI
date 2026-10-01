"""Alur impor web: unggah -> baca & validasi (pratinjau; belum ada yang disimpan) -> simpan (satu transaksi)."""
import hashlib

from django.db import transaction
from django.utils import timezone

from .commit import ImportBlocked, branch_has_data, commit_workbook
from .models import ImportRun
from .reader import WorkbookError, read_workbook
from .schema import load_schema
from .validate import validate

MAX_ISSUES = 500
GROUPS = (("students", "Murid"), ("classes", "Kelas"), ("finance", "Keuangan"), ("masterdata", "Master data"),
          ("quality", "Kualitas data"), ("audit", "Riwayat & audit"))


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def existing_counts(branch):
    return {s.sheet: s.model_class().objects.filter(branch=branch).count() for s in load_schema()}


def build_report(path, branch):
    base = {"ok": False, "fatal": "", "unit": "", "counts": {}, "errors": 0, "warnings": 0, "issues": [], "issues_hidden": 0,
            "existing": existing_counts(branch), "has_data": branch_has_data(branch)}
    try:
        data = read_workbook(path)
    except WorkbookError as exc:
        return {**base, "fatal": str(exc), "errors": 1}
    issues = sorted(validate(data, branch), key=lambda i: (i.level != "error", i.table, i.row or 0))
    errors = sum(1 for i in issues if i.level == "error")
    return {**base, "ok": errors == 0, "unit": data.unit or "", "errors": errors, "warnings": len(issues) - errors,
            "counts": {s.sheet: len(data.tables.get(s.sheet, [])) for s in load_schema()},
            "issues": [i.as_dict() for i in issues[:MAX_ISSUES]], "issues_hidden": max(0, len(issues) - MAX_ISSUES)}


def create_run(uploaded_file, branch, user):
    run = ImportRun(branch=branch, original_name=uploaded_file.name[:255], created_by=user)
    run.file.save(uploaded_file.name, uploaded_file, save=False)
    run.sha256 = sha256_of(run.file.path)
    run.report = build_report(run.file.path, branch)
    run.save()
    return run


def commit_run(run, user, *, replace):
    try:
        with transaction.atomic():
            run = ImportRun.objects.select_for_update().get(pk=run.pk)
            if run.status != "PREVIEW":
                raise ImportBlocked("Impor ini sudah diproses - unggah ulang file bila perlu.")
            if not run.report.get("ok") or sha256_of(run.file.path) != run.sha256:
                raise ImportBlocked("Workbook ini punya error atau berubah sejak pratinjau - perbaiki di Excel lalu unggah ulang.")
            data = read_workbook(run.file.path)
            if any(i.level == "error" for i in validate(data, run.branch)):
                raise ImportBlocked("Workbook ini punya error - perbaiki di Excel lalu unggah ulang.")
            counts = commit_workbook(data, run.branch, user, replace=replace, file_name=run.original_name, sha256=run.sha256)
            run.status, run.committed_by, run.committed_at = "COMMITTED", user, timezone.now()
            run.report = {**run.report, "saved": counts}
            run.save(update_fields=["status", "committed_by", "committed_at", "report"])
    except ImportBlocked:
        raise
    except Exception:
        ImportRun.objects.filter(pk=run.pk, status="PREVIEW").update(status="FAILED")
        raise
    return counts


def grouped_counts(report):
    out = []
    for app, label in GROUPS:
        tables = [{"sheet": s.sheet, "new": report["counts"].get(s.sheet, 0), "existing": report["existing"].get(s.sheet, 0),
                   "saved": report.get("saved", {}).get(s.sheet)} for s in load_schema() if s.app == app]
        out.append({"label": label, "tables": tables, "new": sum(t["new"] for t in tables),
                    "existing": sum(t["existing"] for t in tables)})
    return out
