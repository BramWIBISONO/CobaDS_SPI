"""CatatAudit (VBA Excel): satu baris AUDIT_LOG per perubahan - siapa, kapan, apa, nilai lama -> baru."""
import datetime

from django.db import transaction
from django.utils import timezone

from .ids import next_id, next_row_no


def actor_name(user):
    if user is None:
        return "sistem"
    return getattr(user, "full_name", "") or getattr(user, "email", "") or "sistem"


def _text(value):
    if value is None:
        return ""
    if isinstance(value, datetime.datetime):
        return timezone.localtime(value).strftime("%d %b %Y %H:%M") if timezone.is_aware(value) else value.strftime("%d %b %Y %H:%M")
    if isinstance(value, datetime.date):
        return value.strftime("%d %b %Y")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


@transaction.atomic
def log(*, branch, user, action, entity, entity_id, field="", old="", new="", detected_by="APLIKASI"):
    from audit.models import AuditLog

    return AuditLog.objects.create(
        branch=branch, row_no=next_row_no(AuditLog, branch), lid=next_id(AuditLog, "lid", "LOG-", 6, branch),
        user=actor_name(user), action=action, entity=entity, eid=str(entity_id), field=field,
        old=_text(old), new=_text(new), ts=timezone.now(), by=detected_by)
