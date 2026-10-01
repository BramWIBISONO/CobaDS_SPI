# DIBANGKITKAN oleh tools/generate_models.py dari importer/schema/excel_tables.json - jangan diedit tangan.
# Satu model per tabel Excel v4; kolom FORMULA tidak disimpan (dihitung oleh service).
from django.db import models

from core.models import ExcelRow

__all__ = ['ImportLog', 'SourceReference', 'AuditLog']


class ImportLog(ExcelRow):
    EXCEL_SHEET = 'IMPORT_LOG'
    EXCEL_KEY = 'batch'

    batch = models.CharField('Import Batch', max_length=200, db_index=True)
    date = models.TextField('Import Date', blank=True, default="")
    file = models.TextField('Source File', blank=True, default="")
    path = models.TextField('Source Path', blank=True, default="")
    sha = models.TextField('SHA-256', blank=True, default="")
    sheets = models.TextField('Source Sheets', blank=True, default="")
    rows = models.TextField('Rows Imported', blank=True, default="")
    excluded = models.TextField('Rows Excluded', blank=True, default="")
    ver = models.TextField('Script Version', blank=True, default="")
    notes = models.TextField('Notes', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_import_log"
        verbose_name = 'IMPORT_LOG'
        verbose_name_plural = 'IMPORT_LOG'


class SourceReference(ExcelRow):
    EXCEL_SHEET = 'SOURCE_REFERENCE'
    EXCEL_KEY = 'sid'

    sid = models.CharField('Source ID', max_length=200, db_index=True)
    file = models.TextField('Source File', blank=True, default="")
    sheet = models.TextField('Source Sheet', blank=True, default="")
    role = models.TextField('Peran', blank=True, default="")
    period = models.TextField('Periode', blank=True, default="", db_index=True)
    used = models.TextField('Dipakai di', blank=True, default="")
    rows = models.TextField('Baris', blank=True, default="")
    excluded = models.TextField('Dikecualikan', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_source_reference"
        verbose_name = 'SOURCE_REFERENCE'
        verbose_name_plural = 'SOURCE_REFERENCE'
        constraints = [models.UniqueConstraint(fields=["branch", 'sid'], name="uq_source_reference_key")]


class AuditLog(ExcelRow):
    EXCEL_SHEET = 'AUDIT_LOG'
    EXCEL_KEY = 'lid'

    lid = models.CharField('Log ID', max_length=200, db_index=True)
    user = models.TextField('User', blank=True, default="")
    action = models.TextField('Action', blank=True, default="")
    entity = models.TextField('Entity', blank=True, default="")
    eid = models.TextField('Entity ID', blank=True, default="")
    field = models.TextField('Field', blank=True, default="")
    old = models.TextField('Old Value', blank=True, default="")
    new = models.TextField('New Value', blank=True, default="")
    ts = models.DateTimeField('Timestamp', null=True, blank=True)
    by = models.TextField('Detected By', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_audit_log"
        verbose_name = 'AUDIT_LOG'
        verbose_name_plural = 'AUDIT_LOG'
        constraints = [models.UniqueConstraint(fields=["branch", 'lid'], name="uq_audit_log_key")]
