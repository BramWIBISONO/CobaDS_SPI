"""Catat masuk / keluar / gagal masuk ke SecurityEvent (modul audit log, spesifikasi Super App)."""
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .models import SecurityEvent


def _ip(request):
    return (request.META.get("REMOTE_ADDR") or None) if request is not None else None


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    SecurityEvent.objects.create(user=user, email=user.email, action="LOGIN", ip=_ip(request))


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    if user is not None:
        SecurityEvent.objects.create(user=user, email=user.email, action="LOGOUT", ip=_ip(request))


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    email = str(credentials.get("username") or credentials.get("email") or "")[:254].lower()
    SecurityEvent.objects.create(email=email, action="LOGIN_GAGAL", ip=_ip(request))
