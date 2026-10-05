"""Layanan orang tua / wali (PARENT_MASTER): data, kontak, kontak darurat, anak, catatan komunikasi - selalu dengan audit."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core import audit
from dashboards.calc.base import fold

from .models import ParentMaster, StudentMaster
from .services import SOURCE, _new_parent, _update, find_parent, get_student

EDITABLE = ("nama", "hub", "wa", "email", "alamat", "va", "pref", "kontak_darurat", "telp_darurat")


@transaction.atomic
def create_parent(branch, user, *, nama, hub="", wa="", email="", alamat="", va="", pref="", kontak_darurat="", telp_darurat=""):
    nama = " ".join(str(nama or "").split())
    if not nama:
        raise ValidationError("Nama orang tua wajib diisi.")
    parent = _new_parent(branch, user, nama, hub, wa, email)
    extra = {"alamat": alamat, "va": va, "pref": pref, "kontak_darurat": kontak_darurat, "telp_darurat": telp_darurat}
    for k, v in extra.items():
        setattr(parent, k, v)
    parent.save(update_fields=list(extra))
    return parent


@transaction.atomic
def update_parent(branch, user, pid, **fields):
    parent = find_parent(branch, pid)
    unknown = set(fields) - set(EDITABLE)
    if unknown:
        raise ValidationError(f"Kolom {', '.join(sorted(unknown))} tidak bisa diubah di sini.")
    if "nama" in fields and not " ".join(str(fields["nama"] or "").split()):
        raise ValidationError("Nama orang tua wajib diisi.")
    return _update(branch, user, parent, "PARENT_MASTER", pid, fields)


@transaction.atomic
def link_child(branch, user, pid, std):
    find_parent(branch, pid)
    student = get_student(branch, std)
    return _update(branch, user, student, "STUDENT_MASTER", std, {"par": pid})


@transaction.atomic
def add_communication(branch, user, pid, teks):
    parent = find_parent(branch, pid)
    teks = str(teks or "").strip()
    if not teks:
        raise ValidationError("Catatan komunikasi kosong.")
    stamp = timezone.localtime().strftime("%d %b %Y %H:%M")
    line = f"[{stamp} · {audit.actor_name(user)}] {teks}"
    parent.catatan = f"{parent.catatan}\n{line}" if parent.catatan else line
    parent.save(update_fields=["catatan"])
    audit.log(branch=branch, user=user, action="CREATE", entity="PARENT_MASTER", entity_id=pid, field="Catatan komunikasi", new=teks[:200])
    return parent


def parent_rows(branch, q="", can_see_contacts=False):
    children = {}
    for s in StudentMaster.objects.for_branch(branch).exclude(par="").only("std", "nama", "par"):
        children.setdefault(s.par, []).append(s)
    key = fold(q).strip()
    rows = []
    for p in ParentMaster.objects.for_branch(branch).order_by("nama", "pid"):
        hay = [p.nama, p.pid] + ([p.wa, p.email] if can_see_contacts else []) + [c.nama for c in children.get(p.pid, [])]
        if key and not any(key in fold(h) for h in hay):
            continue
        rows.append({"p": p, "children": children.get(p.pid, [])})
    return rows


__all__ = ["create_parent", "update_parent", "link_child", "add_communication", "parent_rows", "SOURCE"]
