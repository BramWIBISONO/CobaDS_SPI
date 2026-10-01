# DIBANGKITKAN oleh tools/generate_models.py dari importer/schema/excel_tables.json - jangan diedit tangan.
# Satu model per tabel Excel v4; kolom FORMULA tidak disimpan (dihitung oleh service).
from django.db import models

from core.models import ExcelRow

__all__ = ['IssueUnit']


class IssueUnit(ExcelRow):
    EXCEL_SHEET = 'ISSUE_UNIT'
    EXCEL_KEY = 'iid'

    iid = models.CharField('Issue ID', max_length=200, db_index=True)
    unit = models.TextField('Unit', blank=True, default="")
    type = models.TextField('Issue Type', blank=True, default="")
    std = models.TextField('Student ID', blank=True, default="", db_index=True)
    nama = models.TextField('Nama Murid', blank=True, default="")
    code = models.TextField('Kode Kelas', blank=True, default="", db_index=True)
    month = models.DateField('Month', null=True, blank=True)
    source = models.TextField('Source', blank=True, default="")
    desc = models.TextField('Issue Description', blank=True, default="")
    expected = models.TextField('Expected Value', blank=True, default="")
    actual = models.TextField('Actual Value', blank=True, default="")
    sev = models.TextField('Severity', blank=True, default="")
    status = models.TextField('Status', blank=True, default="")
    assigned = models.TextField('Assigned To', blank=True, default="")
    reviewer = models.TextField('Reviewer', blank=True, default="")
    created = models.DateField('Created Date', null=True, blank=True)
    resolved = models.DateField('Resolved Date', null=True, blank=True)
    resolution = models.TextField('Resolution', blank=True, default="")
    evidence = models.TextField('Evidence', blank=True, default="")
    still = models.TextField('Kondisi Masih Ada', blank=True, default="")
    kat = models.TextField('Kategori', blank=True, default="")
    s360 = models.FloatField('S360', null=True, blank=True)

    class Meta(ExcelRow.Meta):
        db_table = "x_issue_unit"
        verbose_name = 'ISSUE_UNIT'
        verbose_name_plural = 'ISSUE_UNIT'
        constraints = [models.UniqueConstraint(fields=["branch", 'iid'], name="uq_issue_unit_key")]
