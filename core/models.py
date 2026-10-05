from django.db import models


class BranchQuerySet(models.QuerySet):
    def for_branch(self, branch):
        return self.filter(branch=branch)


class ExcelRow(models.Model):
    """Satu baris tabel Excel v4. Setiap baris milik satu cabang; row_no menjaga urutan baris seperti di sheet."""
    EXCEL_SHEET = ""
    EXCEL_KEY = ""
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="+")
    row_no = models.PositiveIntegerField("Baris", default=0, db_index=True)

    objects = BranchQuerySet.as_manager()

    class Meta:
        abstract = True
        ordering = ["row_no", "pk"]

    def __str__(self):
        return str(getattr(self, self.EXCEL_KEY, "") or self.pk)


class Notifikasi(models.Model):
    """Notifikasi di dalam aplikasi untuk satu pengguna di satu cabang (follow-up ditugaskan, pembayaran menunggu verifikasi, ...)."""
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="notifikasi")
    branch = models.ForeignKey("branches.Branch", on_delete=models.CASCADE, related_name="+")
    kind = models.CharField("Jenis", max_length=40, blank=True, default="")
    title = models.CharField("Judul", max_length=200)
    body = models.TextField("Isi", blank=True, default="")
    url = models.CharField("Tautan", max_length=300, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=["user", "branch", "read_at"])]

    def __str__(self):
        return self.title
