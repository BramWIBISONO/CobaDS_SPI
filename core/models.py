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
