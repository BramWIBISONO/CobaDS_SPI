# DIBANGKITKAN oleh tools/generate_models.py dari importer/schema/excel_tables.json - jangan diedit tangan.
# Satu model per tabel Excel v4; kolom FORMULA tidak disimpan (dihitung oleh service).
from django.db import models

from core.models import ExcelRow

__all__ = ['ClassMaster', 'ClassMembers', 'ClassSchedule', 'SimulasiJadwal', 'Sesi']


class ClassMaster(ExcelRow):
    EXCEL_SHEET = 'CLASS_MASTER'
    EXCEL_KEY = 'class_id'

    class_id = models.CharField('Class ID', max_length=200, db_index=True)
    code = models.TextField('Kode Kelas', blank=True, default="", db_index=True)
    unit = models.TextField('Unit', blank=True, default="")
    bahasa = models.TextField('Bahasa', blank=True, default="")
    tipe = models.TextField('Tipe Kelas', blank=True, default="")
    program = models.TextField('Program', blank=True, default="")
    level = models.TextField('Level', blank=True, default="")
    guru = models.TextField('Guru', blank=True, default="")
    mode = models.TextField('Mode', blank=True, default="")
    sekolah = models.TextField('Sekolah', blank=True, default="")
    start = models.DateField('Tanggal Mulai (bulan kode)', null=True, blank=True)
    end = models.DateField('Tanggal Selesai (aktif terakhir)', null=True, blank=True)
    fmt = models.TextField('Format Kode', blank=True, default="")
    status_kode = models.TextField('Status Kode', blank=True, default="")
    verdict = models.TextField('Pembacaan', blank=True, default="")
    year = models.FloatField('Tahun Kode', null=True, blank=True)
    month = models.FloatField('Bulan Kode', null=True, blank=True)
    seq = models.TextField('Urutan', blank=True, default="")
    cands = models.TextField('Kandidat Pembacaan', blank=True, default="")
    n_hist = models.FloatField('Murid dalam Riwayat', null=True, blank=True)
    sheets = models.TextField('Ditemukan di Sheet', blank=True, default="")
    n_occ = models.FloatField('Jumlah Kemunculan', null=True, blank=True)
    val_status = models.TextField('Validation Status', blank=True, default="")
    val_by = models.TextField('Validator', blank=True, default="")
    val_date = models.TextField('Validation Date', blank=True, default="")
    val_note = models.TextField('Catatan Validator', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_class_master"
        verbose_name = 'CLASS_MASTER'
        verbose_name_plural = 'CLASS_MASTER'
        constraints = [models.UniqueConstraint(fields=["branch", 'class_id'], name="uq_class_master_key")]


class ClassMembers(ExcelRow):
    EXCEL_SHEET = 'CLASS_MEMBERS'
    EXCEL_KEY = 'mbr'

    code = models.TextField('Kode Kelas', blank=True, default="", db_index=True)
    std = models.TextField('Student ID', blank=True, default="", db_index=True)
    nama = models.TextField('Nama Murid', blank=True, default="")
    status_plain = models.TextField('Status Keanggotaan', blank=True, default="")
    months_all = models.TextField('Periode Terlihat', blank=True, default="")
    join = models.DateField('Join Date', null=True, blank=True)
    join_text = models.TextField('Join Date (teks asli)', blank=True, default="")
    program = models.TextField('Program', blank=True, default="")
    level = models.TextField('Level', blank=True, default="")
    guru = models.TextField('Guru', blank=True, default="")
    mode = models.TextField('Mode', blank=True, default="")
    sekolah = models.TextField('Sekolah', blank=True, default="")
    sources_plain = models.TextField('Sumber', blank=True, default="")
    kepastian = models.TextField('Kepastian', blank=True, default="")
    val_status = models.TextField('Validation Status', blank=True, default="")
    val_by = models.TextField('Validator', blank=True, default="")
    val_date = models.TextField('Validation Date', blank=True, default="")
    val_note = models.TextField('Catatan Validator', blank=True, default="")
    mbr = models.CharField('Membership ID', max_length=200, db_index=True)
    class_id = models.TextField('Class ID', blank=True, default="", db_index=True)
    std_usulan = models.TextField('Student ID (usulan)', blank=True, default="")
    nama_sumber = models.TextField('Nama di Sumber', blank=True, default="")
    v1 = models.TextField('ID v1', blank=True, default="")
    kode_saat_ini = models.TextField('Kode Saat Ini (DB Murid)', blank=True, default="")
    status = models.TextField('Status Membership', blank=True, default="")
    start = models.DateField('Start Date (bukti)', null=True, blank=True)
    end = models.DateField('End Date (bukti)', null=True, blank=True)
    bukti = models.TextField('Bukti', blank=True, default="")
    match = models.TextField('Match Status', blank=True, default="")
    conf = models.TextField('Matching Confidence', blank=True, default="")
    method = models.TextField('Dasar Pencocokan', blank=True, default="")
    prov_file = models.TextField('Source File', blank=True, default="")
    prov_sheet = models.TextField('Source Sheet', blank=True, default="")
    prov_row = models.TextField('Source Row', blank=True, default="")
    prov_type = models.TextField('Source Type', blank=True, default="")
    prov_batch = models.TextField('Import Batch', blank=True, default="")
    prov_date = models.DateField('Import Date', null=True, blank=True)
    s360 = models.FloatField('S360', null=True, blank=True)

    class Meta(ExcelRow.Meta):
        db_table = "x_class_members"
        verbose_name = 'CLASS_MEMBERS'
        verbose_name_plural = 'CLASS_MEMBERS'
        constraints = [models.UniqueConstraint(fields=["branch", 'mbr'], name="uq_class_members_key")]


class ClassSchedule(ExcelRow):
    EXCEL_SHEET = 'CLASS_SCHEDULE'
    EXCEL_KEY = 'sid'

    sid = models.CharField('Schedule ID', max_length=200, db_index=True)
    code = models.TextField('Class Code', blank=True, default="")
    class_id = models.TextField('Class ID', blank=True, default="", db_index=True)
    day = models.TextField('Day', blank=True, default="")
    session = models.TextField('Sesi', blank=True, default="")
    start = models.TimeField('Start Time', null=True, blank=True)
    end = models.TimeField('End Time', null=True, blank=True)
    time_in_text = models.TextField('Jam di Teks', blank=True, default="")
    room = models.TextField('Room', blank=True, default="")
    room_id = models.TextField('Room ID', blank=True, default="")
    mode = models.TextField('Mode', blank=True, default="")
    teacher = models.TextField('Teacher', blank=True, default="")
    teacher_id = models.TextField('Teacher ID', blank=True, default="", db_index=True)
    eff_from = models.TextField('Effective From', blank=True, default="")
    eff_until = models.TextField('Effective Until', blank=True, default="")
    text = models.TextField('Teks Kelas Asli', blank=True, default="")
    level_text = models.TextField('Level di Teks', blank=True, default="")
    lang_text = models.TextField('Bahasa di Teks', blank=True, default="")
    murid_usulan = models.TextField('Murid di Teks (usulan)', blank=True, default="")
    flag = models.TextField('Catatan', blank=True, default="")
    prov_file = models.TextField('Source File', blank=True, default="")
    prov_sheet = models.TextField('Source Sheet', blank=True, default="")
    prov_row = models.TextField('Source Row', blank=True, default="")
    prov_type = models.TextField('Source Type', blank=True, default="")
    prov_batch = models.TextField('Import Batch', blank=True, default="")
    prov_date = models.DateField('Import Date', null=True, blank=True)

    class Meta(ExcelRow.Meta):
        db_table = "x_class_schedule"
        verbose_name = 'CLASS_SCHEDULE'
        verbose_name_plural = 'CLASS_SCHEDULE'
        constraints = [models.UniqueConstraint(fields=["branch", 'sid'], name="uq_class_schedule_key")]


class SimulasiJadwal(ExcelRow):
    EXCEL_SHEET = 'SIMULASI_JADWAL'
    EXCEL_KEY = 'no'

    no = models.CharField('No Simulasi', max_length=200, db_index=True)
    murid = models.TextField('Murid', blank=True, default="")
    hari = models.TextField('Hari', blank=True, default="")
    mulai = models.TimeField('Jam Mulai', null=True, blank=True)
    selesai = models.TimeField('Jam Selesai', null=True, blank=True)
    guru = models.TextField('Guru', blank=True, default="")
    kode = models.TextField('Kode Kelas', blank=True, default="", db_index=True)
    ruang = models.TextField('Ruang', blank=True, default="")
    status = models.TextField('Status Rencana', blank=True, default="")
    catatan = models.TextField('Catatan', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_simulasi_jadwal"
        verbose_name = 'SIMULASI_JADWAL'
        verbose_name_plural = 'SIMULASI_JADWAL'
        constraints = [models.UniqueConstraint(fields=["branch", 'no'], name="uq_simulasi_jadwal_key")]


class Sesi(ExcelRow):
    EXCEL_SHEET = 'SESI'
    EXCEL_KEY = 'sid'

    sid = models.CharField('Sesi ID', max_length=200, db_index=True)
    per = models.TextField('Periode', blank=True, default="", db_index=True)
    tgl = models.DateField('Tanggal', null=True, blank=True)
    hari = models.TextField('Hari', blank=True, default="")
    mulai = models.TimeField('Mulai', null=True, blank=True)
    selesai = models.TimeField('Selesai', null=True, blank=True)
    guru = models.TextField('Guru', blank=True, default="")
    kode = models.TextField('Kode Kelas', blank=True, default="", db_index=True)
    kelas = models.TextField('Kelas (teks)', blank=True, default="")
    ruang = models.TextField('Ruang', blank=True, default="")
    slot = models.TextField('Slot Jadwal', blank=True, default="")
    status = models.TextField('Status Sesi', blank=True, default="")
    hadir = models.FloatField('Murid Hadir', null=True, blank=True)
    absen = models.TextField('Murid Tidak Hadir', blank=True, default="")
    konf_oleh = models.TextField('Dikonfirmasi Oleh', blank=True, default="")
    konf_pada = models.DateTimeField('Dikonfirmasi Pada', null=True, blank=True)
    catatan = models.TextField('Catatan', blank=True, default="")
    sumber = models.TextField('Sumber', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_sesi"
        verbose_name = 'SESI'
        verbose_name_plural = 'SESI'
        constraints = [models.UniqueConstraint(fields=["branch", 'sid'], name="uq_sesi_key")]
