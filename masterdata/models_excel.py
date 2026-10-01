# DIBANGKITKAN oleh tools/generate_models.py dari importer/schema/excel_tables.json - jangan diedit tangan.
# Satu model per tabel Excel v4; kolom FORMULA tidak disimpan (dihitung oleh service).
from django.db import models

from core.models import ExcelRow

__all__ = ['OffReasonMaster', 'TeacherMaster', 'ProgramMaster', 'PartnerMaster', 'RoomMaster', 'UnitMaster', 'TarifFee']


class OffReasonMaster(ExcelRow):
    EXCEL_SHEET = 'OFF_REASON_MASTER'
    EXCEL_KEY = 'rid'

    rid = models.CharField('Reason ID', max_length=200, db_index=True)
    text = models.TextField('Alasan Asli', blank=True, default="")
    murid = models.TextField('Murid yang Off (bulan Off)', blank=True, default="")
    cat_final = models.TextField('Ganti Kategori (bila salah)', blank=True, default="")
    source = models.TextField('Sumber', blank=True, default="")
    val_status = models.TextField('Validation Status', blank=True, default="")
    val_by = models.TextField('Validator', blank=True, default="")
    val_date = models.TextField('Validation Date', blank=True, default="")
    val_note = models.TextField('Catatan Validator', blank=True, default="")
    cat = models.TextField('Kategori Usulan Sistem', blank=True, default="")
    cells = models.TextField('Sel Sumber (contoh)', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_off_reason_master"
        verbose_name = 'OFF_REASON_MASTER'
        verbose_name_plural = 'OFF_REASON_MASTER'
        constraints = [models.UniqueConstraint(fields=["branch", 'rid'], name="uq_off_reason_master_key")]


class TeacherMaster(ExcelRow):
    EXCEL_SHEET = 'TEACHER_MASTER'
    EXCEL_KEY = 'tid'

    tid = models.CharField('Teacher ID', max_length=200, db_index=True)
    emp = models.TextField('Employee ID', blank=True, default="")
    name = models.TextField('Name', blank=True, default="")
    phone = models.TextField('Phone', blank=True, default="")
    email = models.TextField('Email', blank=True, default="")
    spec = models.TextField('Specialization', blank=True, default="")
    emp_type = models.TextField('Employment Type', blank=True, default="")
    unit = models.TextField('Unit ID', blank=True, default="")
    status = models.TextField('Status', blank=True, default="")
    basis = models.TextField('Dasar Status', blank=True, default="")
    join = models.DateField('Join Date', null=True, blank=True)
    sources = models.TextField('Source', blank=True, default="")
    variants = models.TextField('Varian Nama di Sumber', blank=True, default="")
    first = models.DateField('Bulan Pertama Terlihat', null=True, blank=True)
    last = models.DateField('Bulan Terakhir Terlihat', null=True, blank=True)
    emp_name = models.TextField('Nama Lengkap (payroll)', blank=True, default="")
    emp_cell = models.TextField('Sel Payroll', blank=True, default="")
    usulan = models.TextField('Mungkin Orang yang Sama', blank=True, default="")
    val_status = models.TextField('Validation Status', blank=True, default="")
    val_by = models.TextField('Validator', blank=True, default="")
    val_date = models.TextField('Validation Date', blank=True, default="")
    val_note = models.TextField('Catatan Validator', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_teacher_master"
        verbose_name = 'TEACHER_MASTER'
        verbose_name_plural = 'TEACHER_MASTER'
        constraints = [models.UniqueConstraint(fields=["branch", 'tid'], name="uq_teacher_master_key")]


class ProgramMaster(ExcelRow):
    EXCEL_SHEET = 'PROGRAM_MASTER'
    EXCEL_KEY = 'pid'

    pid = models.CharField('Program ID', max_length=200, db_index=True)
    bu = models.TextField('Business Unit', blank=True, default="")
    program = models.TextField('Program', blank=True, default="")
    level = models.TextField('Level', blank=True, default="")
    kode = models.TextField('Kode Level', blank=True, default="")
    order = models.FloatField('Urutan', null=True, blank=True)
    variants = models.TextField('Varian di Sumber', blank=True, default="")
    status = models.TextField('Status', blank=True, default="")
    n_months = models.FloatField('Murid-Bulan Tercatat', null=True, blank=True)
    sources = models.TextField('Source', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_program_master"
        verbose_name = 'PROGRAM_MASTER'
        verbose_name_plural = 'PROGRAM_MASTER'
        constraints = [models.UniqueConstraint(fields=["branch", 'pid'], name="uq_program_master_key")]


class PartnerMaster(ExcelRow):
    EXCEL_SHEET = 'PARTNER_MASTER'
    EXCEL_KEY = 'pid'

    pid = models.CharField('Partner ID', max_length=200, db_index=True)
    name = models.TextField('Name', blank=True, default="")
    type = models.TextField('Type', blank=True, default="")
    contact = models.TextField('Contact Person', blank=True, default="")
    phone = models.TextField('Phone', blank=True, default="")
    email = models.TextField('Email', blank=True, default="")
    address = models.TextField('Address', blank=True, default="")
    city = models.TextField('City', blank=True, default="")
    status = models.TextField('Status', blank=True, default="")
    sources = models.TextField('Source', blank=True, default="")
    variants = models.TextField('Varian Nama', blank=True, default="")
    usulan = models.TextField('Mungkin Sekolah yang Sama', blank=True, default="")
    keputusan = models.TextField('Keputusan Varian', blank=True, default="")
    val_status = models.TextField('Validation Status', blank=True, default="")
    val_by = models.TextField('Validator', blank=True, default="")
    val_date = models.TextField('Validation Date', blank=True, default="")
    val_note = models.TextField('Catatan Validator', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_partner_master"
        verbose_name = 'PARTNER_MASTER'
        verbose_name_plural = 'PARTNER_MASTER'
        constraints = [models.UniqueConstraint(fields=["branch", 'pid'], name="uq_partner_master_key")]


class RoomMaster(ExcelRow):
    EXCEL_SHEET = 'ROOM_MASTER'
    EXCEL_KEY = 'rid'

    rid = models.CharField('Room ID', max_length=200, db_index=True)
    name = models.TextField('Room Name', blank=True, default="")
    type = models.TextField('Type', blank=True, default="")
    cap = models.TextField('Capacity', blank=True, default="")
    unit = models.TextField('Unit ID', blank=True, default="")
    status = models.TextField('Status', blank=True, default="")
    source = models.TextField('Source', blank=True, default="")
    variants = models.TextField('Varian Nama', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_room_master"
        verbose_name = 'ROOM_MASTER'
        verbose_name_plural = 'ROOM_MASTER'
        constraints = [models.UniqueConstraint(fields=["branch", 'rid'], name="uq_room_master_key")]


class UnitMaster(ExcelRow):
    EXCEL_SHEET = 'UNIT_MASTER'
    EXCEL_KEY = 'uid'

    uid = models.CharField('Unit ID', max_length=200, db_index=True)
    name = models.TextField('Unit Name', blank=True, default="")
    type = models.TextField('Unit Type', blank=True, default="")
    parent = models.TextField('Parent Unit', blank=True, default="")
    city = models.TextField('City', blank=True, default="")
    province = models.TextField('Province', blank=True, default="")
    status = models.TextField('Status', blank=True, default="")
    notes = models.TextField('Notes', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_unit_master"
        verbose_name = 'UNIT_MASTER'
        verbose_name_plural = 'UNIT_MASTER'
        constraints = [models.UniqueConstraint(fields=["branch", 'uid'], name="uq_unit_master_key")]


class TarifFee(ExcelRow):
    EXCEL_SHEET = 'TARIF_FEE'
    EXCEL_KEY = 'rid'

    rid = models.CharField('Tarif ID', max_length=200, db_index=True)
    tipe = models.TextField('Tipe Kelas', blank=True, default="")
    program = models.TextField('Program', blank=True, default="")
    bahasa = models.TextField('Bahasa', blank=True, default="")
    tarif = models.FloatField('Tarif per Sesi', null=True, blank=True)
    dasar = models.TextField('Dasar Tarif', blank=True, default="")
    mulai = models.DateField('Berlaku Mulai', null=True, blank=True)
    sumber = models.TextField('Sumber Tarif', blank=True, default="")
    catatan = models.TextField('Catatan', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_tarif_fee"
        verbose_name = 'TARIF_FEE'
        verbose_name_plural = 'TARIF_FEE'
        constraints = [models.UniqueConstraint(fields=["branch", 'rid'], name="uq_tarif_fee_key")]
