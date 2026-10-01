"""Menyimpan isi workbook ke database dalam satu transaksi (semua atau tidak sama sekali).

- Tabel Excel: isi cabang diganti isi workbook; row_no = nomor baris sheet (urutan sama dengan Excel).
- Riwayat (AUDIT_LOG, IMPORT_LOG): tidak pernah dihapus/diubah. Baris workbook yang isinya sudah tersimpan dilewati; Log ID Excel dipakai
  kecuali sudah dipakai catatan lain (lalu diberi Log ID berikutnya dan dicatat di IMPORT_LOG).
- SETTINGS (v2_build_sheets.py SET_ROWS): identitas -> Branch; branch_id dicek validasi; unit = Branch.unit_id; baris rumus dihitung web
  (tidak disimpan) kecuali 'ambang' (=ambang menunjuk sel isian CEK_SPP!B3); baris lain -> BranchSetting."""
import datetime

from django.db import transaction
from django.utils import timezone

from audit.models import ImportLog
from branches.models import Branch, BranchSetting
from core import audit
from core.ids import next_id, next_row_no

from .convert import convert
from .schema import load_schema

LOG_TABLES = {"AUDIT_LOG": ("LOG-", 6), "IMPORT_LOG": None}        # (awalan, digit) untuk ID baru bila ID Excel sudah dipakai
IDENTITY_KEYS = {"branch_name": "name", "branch_city": "city", "branch_address": "address", "branch_status": "status",
                 "branch_lang": "language", "branch_currency": "currency", "branch_open": "opening_date"}
NOT_STORED_KEYS = {"branch_id", "unit"}
STORED_FORMULA_KEYS = {"ambang"}
IMPORT_VERSION = "web tahap 1A"


class ImportBlocked(Exception):
    pass


def branch_has_data(branch):
    """Data cabang = baris tabel Excel mana pun (riwayat tidak dihitung) atau parameter SETTINGS."""
    if BranchSetting.objects.filter(branch=branch).exists():
        return True
    return any(s.model_class().objects.filter(branch=branch).exists() for s in load_schema() if s.sheet not in LOG_TABLES)


def _names(spec):
    names = []
    for f in spec.stored_fields:
        names += [f.name, f.text_field] if f.text_field else [f.name]
    return names


def _build(spec, rows, branch):
    model = spec.model_class()
    objs = []
    for r in rows:
        values = {}
        for f in spec.stored_fields:
            values.update(convert(f, r.values.get(f.name)))
        objs.append(model(branch=branch, row_no=r.row, **values))
    return objs


def _replace(spec, rows, branch):
    model = spec.model_class()
    model.objects.filter(branch=branch).delete()
    model.objects.bulk_create(_build(spec, rows, branch), batch_size=1000)
    return len(rows)


def _merge_log(spec, rows, branch):
    model, id_rule = spec.model_class(), LOG_TABLES[spec.sheet]
    content = [n for n in _names(spec) if not (id_rule and n == spec.key)]
    current = list(model.objects.for_branch(branch))
    stored = {tuple(getattr(o, n) for n in content) for o in current}
    used = {getattr(o, spec.key) for o in current}
    last_row = max((o.row_no for o in current), default=None)     # tabel kosong: nomor baris Excel dipakai
    added = renumbered = 0
    for obj in _build(spec, rows, branch):
        if tuple(getattr(obj, n) for n in content) in stored:
            continue
        if id_rule and getattr(obj, spec.key) in used:
            setattr(obj, spec.key, next_id(model, spec.key, *id_rule, branch))
            renumbered += 1
        if last_row is not None:
            last_row += 1
            obj.row_no = last_row
        obj.save()
        used.add(getattr(obj, spec.key))
        added += 1
    return added, renumbered


def _identity_value(field, v):
    if field == "opening_date":
        if isinstance(v, datetime.datetime):
            return v.date()
        return v if isinstance(v, datetime.date) else None
    return "" if v is None else str(v).strip()


def stored_settings(settings):
    """Baris SETTINGS yang disimpan sebagai BranchSetting (juga dipakai template cabang baru, Task 10)."""
    return [s for s in settings if s["key"] not in IDENTITY_KEYS and s["key"] not in NOT_STORED_KEYS
            and (not s["is_formula"] or s["key"] in STORED_FORMULA_KEYS)]


def _apply_settings(data, branch, user):
    changed = []
    for s in data.settings:
        field = IDENTITY_KEYS.get(s["key"])
        if field is None:
            continue
        value = _identity_value(field, s["value"])
        if (field == "name" and not value) or (field == "status" and value not in dict(Branch.STATUS_CHOICES)):
            continue                                   # nama wajib; status dibatasi daftar (validasi data Excel): nilai lama dipakai
        old = getattr(branch, field)
        if old != value:
            setattr(branch, field, value)
            changed.append((field, old, value))
    if changed:
        branch.save(update_fields=[f for f, _old, _new in changed])
        for field, old, value in changed:
            audit.log(branch=branch, user=user, action="UPDATE", entity="CABANG", entity_id=branch.code,
                      field=str(Branch._meta.get_field(field).verbose_name), old=old, new=value)
    BranchSetting.objects.filter(branch=branch).delete()
    BranchSetting.objects.bulk_create([
        BranchSetting(branch=branch, key=s["key"], label=str(s["param"]), note=str(s["note"]), row_no=s["row"],
                      **BranchSetting.split_value(s["value"]))
        for s in stored_settings(data.settings)])


def _log_import(branch, *, file_name, sha256, source_path, counts, notes):
    now = timezone.localtime()
    batch = next_id(ImportLog, "batch", f"IMP-{branch.unit_id[len('UNIT-'):]}-{now:%Y%m%d}-", 2, branch)
    ImportLog.objects.create(
        branch=branch, row_no=next_row_no(ImportLog, branch), batch=batch, date=now.strftime("%Y-%m-%d %H:%M"), file=file_name,
        path=source_path or "unggahan web", sha=sha256, sheets=f"{len(counts)} tabel + SETTINGS",
        rows="; ".join(f"{sheet} {n}" for sheet, n in counts.items() if n) or "0 baris",
        excluded="kolom rumus (dihitung aplikasi web)", ver=IMPORT_VERSION, notes="; ".join(notes))
    return batch


@transaction.atomic
def commit_workbook(data, branch, user, *, replace, file_name, sha256, source_path="", note=""):
    list(Branch.objects.select_for_update().filter(pk=branch.pk).values_list("pk", flat=True))   # satu impor per cabang
    had_data = branch_has_data(branch)
    if had_data and not replace:
        raise ImportBlocked(f"{branch.name} sudah berisi data. Pilih 'ganti semua data cabang' untuk menggantinya dengan isi workbook ini.")
    counts, notes = {}, [n for n in (note, "ganti semua data cabang" if had_data else "") if n]
    for spec in load_schema():
        rows = data.tables.get(spec.sheet, [])
        if spec.sheet in LOG_TABLES:
            counts[spec.sheet], renumbered = _merge_log(spec, rows, branch)
            if renumbered:
                notes.append(f"{renumbered} baris {spec.sheet} workbook mendapat Log ID baru (ID Excel sudah dipakai catatan web)")
        else:
            counts[spec.sheet] = _replace(spec, rows, branch)
    _apply_settings(data, branch, user)                # sesudah riwayat workbook: catatan web mendapat Log ID sesudahnya
    batch = _log_import(branch, file_name=file_name, sha256=sha256, source_path=source_path, counts=counts, notes=notes)
    audit.log(branch=branch, user=user, action="IMPORT", entity="WORKBOOK", entity_id=file_name,
              new=" · ".join([batch, f"{sum(counts.values())} baris", *notes]))
    return counts
