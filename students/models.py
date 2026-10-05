from django.conf import settings
from django.db import models

from .models_excel import *  # noqa: F401,F403  (tabel Excel v4 yang dibangkitkan)


class CatatanMurid(models.Model):
    """Catatan bebas staf tentang seorang murid (tampil di profil & riwayat). Murid dirujuk dengan Student ID per cabang."""
    branch = models.ForeignKey("branches.Branch", on_delete=models.CASCADE, related_name="+")
    std = models.CharField("Student ID", max_length=40, db_index=True)
    teks = models.TextField("Catatan")
    dibuat_oleh = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-dibuat_pada", "-pk"]
        indexes = [models.Index(fields=["branch", "std"])]

    def __str__(self):
        return f"{self.std}: {self.teks[:40]}"
