from django.conf import settings
from django.db import models


class ImportRun(models.Model):
    """Satu unggahan workbook: pratinjau (belum ada yang disimpan) -> tersimpan / gagal. File di MEDIA_ROOT, tidak dilayani publik."""
    STATUS_CHOICES = [("PREVIEW", "Pratinjau"), ("COMMITTED", "Tersimpan"), ("FAILED", "Gagal")]
    branch = models.ForeignKey("branches.Branch", on_delete=models.CASCADE, related_name="import_runs")
    file = models.FileField(upload_to="imports/%Y/%m/")
    original_name = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=64)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PREVIEW")
    report = models.JSONField(default=dict)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    committed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    committed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.branch.code} · {self.original_name} · {self.status}"
