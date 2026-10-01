"""IdBaru (VBA Excel): nomor berikutnya setelah nomor tertinggi dengan awalan itu - nomor tidak pernah dipakai dua kali."""
from django.db import transaction
from django.db.models import Max

from branches.models import Branch


def next_id(model, field, prefix, digits, branch):
    """Harus dipanggil di dalam transaction.atomic(): baris cabang dikunci agar dua pengguna tidak mendapat nomor yang sama."""
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("next_id() harus dipanggil di dalam transaction.atomic()")
    list(Branch.objects.select_for_update().filter(pk=branch.pk).values_list("pk", flat=True))
    top = 0
    for value in model.objects.filter(branch=branch, **{f"{field}__startswith": prefix}).values_list(field, flat=True):
        rest = str(value)[len(prefix):]
        if rest.isdigit() and len(rest) < 10:
            top = max(top, int(rest))
    return f"{prefix}{top + 1:0{digits}d}"


def next_row_no(model, branch):
    return (model.objects.filter(branch=branch).aggregate(m=Max("row_no"))["m"] or 0) + 1
