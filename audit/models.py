from django.conf import settings
from django.db import models

from .models_excel import *  # noqa: F401,F403  (tabel Excel v4 yang dibangkitkan)


class SecurityEvent(models.Model):
    """Masuk, keluar, dan gagal masuk (tidak terikat cabang). Kata sandi tidak pernah disimpan."""
    ACTIONS = [("LOGIN", "Masuk"), ("LOGOUT", "Keluar"), ("LOGIN_GAGAL", "Gagal masuk")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    email = models.CharField("Email", max_length=254, blank=True, default="")
    action = models.CharField("Aksi", max_length=20, choices=ACTIONS)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "Riwayat keamanan"
        verbose_name_plural = "Riwayat keamanan"
