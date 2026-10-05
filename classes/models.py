from django.conf import settings
from django.db import models

from .models_excel import *  # noqa: F401,F403  (tabel Excel v4 yang dibangkitkan)


class Kehadiran(models.Model):
    """Kehadiran satu murid di satu sesi (unik per cabang+sesi+murid). Sesi & murid dirujuk dengan ID bisnis per cabang."""
    STATUS = [("HADIR", "Hadir"), ("TERLAMBAT", "Terlambat"), ("IZIN", "Izin"), ("ABSEN", "Tidak hadir")]
    PRESENT = ("HADIR", "TERLAMBAT")
    branch = models.ForeignKey("branches.Branch", on_delete=models.CASCADE, related_name="+")
    sid = models.CharField("Sesi ID", max_length=60, db_index=True)
    std = models.CharField("Student ID", max_length=40, db_index=True)
    status = models.CharField("Status", max_length=12, choices=STATUS)
    catatan = models.CharField("Catatan", max_length=300, blank=True, default="")
    dicatat_oleh = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    dicatat_pada = models.DateTimeField(auto_now_add=True)
    diubah_pada = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sid", "std"]
        constraints = [models.UniqueConstraint(fields=["branch", "sid", "std"], name="uq_kehadiran_sesi_murid")]
        indexes = [models.Index(fields=["branch", "std"])]

    def __str__(self):
        return f"{self.sid} {self.std} {self.status}"
