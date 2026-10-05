"""Perubahan kolom dengan jejak audit: satu baris AUDIT_LOG per kolom yang benar-benar berubah (CatatAudit VBA)."""
from . import audit


def apply_changes(branch, user, obj, entity, entity_id, changes):
    changed = []
    for name, new in changes.items():
        old = getattr(obj, name)
        if old == new or (old in (None, "") and new in (None, "")):
            continue
        setattr(obj, name, new)
        changed.append(name)
        field = obj._meta.get_field(name)
        shown_old = getattr(old, "display_name", old)
        shown_new = getattr(new, "display_name", new)
        audit.log(branch=branch, user=user, action="UPDATE", entity=entity, entity_id=entity_id,
                  field=str(field.verbose_name), old=shown_old, new=shown_new)
    if changed:
        obj.save(update_fields=changed)
    return changed
