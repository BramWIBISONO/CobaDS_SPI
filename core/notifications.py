"""Notifikasi di dalam aplikasi: dibuat oleh service saat ada pekerjaan untuk seseorang, dibaca di lonceng topbar."""
from django.utils import timezone

from .models import Notifikasi


def notify(user, branch, title, body="", *, url="", kind=""):
    if user is None:
        return None
    return Notifikasi.objects.create(user=user, branch=branch, title=title[:200], body=body, url=url, kind=kind)


def notify_many(users, branch, title, body="", *, url="", kind=""):
    return [notify(u, branch, title, body, url=url, kind=kind) for u in users]


def unread_count(user, branch):
    if branch is None or not getattr(user, "is_authenticated", False):
        return 0
    return Notifikasi.objects.filter(user=user, branch=branch, read_at__isnull=True).count()


def mark_read(notifikasi):
    if notifikasi.read_at is None:
        notifikasi.read_at = timezone.now()
        notifikasi.save(update_fields=["read_at"])
