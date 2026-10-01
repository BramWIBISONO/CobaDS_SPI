# DIBANGKITKAN oleh tools/generate_models.py dari importer/schema/excel_tables.json - jangan diedit tangan.
# Satu model per tabel Excel v4; kolom FORMULA tidak disimpan (dihitung oleh service).
from django.db import models

from core.models import ExcelRow

__all__ = ['StudentMaster', 'StudentIdMapping', 'StudentOff', 'StatusEvent', 'ParentMaster', 'FollowUp', 'AcademicRecord', 'Lead', 'Dokumen', 'DBulan', 'DMurid']


class StudentMaster(ExcelRow):
    EXCEL_SHEET = 'STUDENT_MASTER'
    EXCEL_KEY = 'std'

    std = models.CharField('Student ID', max_length=200, db_index=True)
    v1 = models.TextField('ID v1', blank=True, default="")
    nama = models.TextField('Nama Murid', blank=True, default="")
    nama_asli = models.TextField('Nama Asli', blank=True, default="")
    kode_raw = models.TextField('Kode Kelas', blank=True, default="", db_index=True)
    kode_status = models.TextField('Status Kode Kelas', blank=True, default="")
    bahasa = models.TextField('Bahasa', blank=True, default="")
    tipe_kode = models.TextField('Tipe (dari kode)', blank=True, default="")
    tipe_asli = models.TextField('Tipe Kelas (DB Murid)', blank=True, default="")
    program = models.TextField('Program', blank=True, default="")
    level = models.TextField('Level', blank=True, default="")
    guru = models.TextField('Guru', blank=True, default="")
    mode = models.TextField('Mode', blank=True, default="")
    sekolah = models.TextField('Sekolah', blank=True, default="")
    partner_id = models.TextField('Partner ID', blank=True, default="")
    kota = models.TextField('Kota', blank=True, default="")
    unit = models.TextField('Unit ID', blank=True, default="")
    join = models.DateField('Join', null=True, blank=True)
    join_text = models.TextField('Join (teks asli)', blank=True, default="")
    harga = models.FloatField('Harga SPP', null=True, blank=True)
    harga_text = models.TextField('Harga SPP (teks asli)', blank=True, default="")
    status_last = models.TextField('Status Terakhir', blank=True, default="")
    month_last = models.DateField('Bulan Status', null=True, blank=True)
    st_base = models.TextField('Status Awal (Sep 2026)', blank=True, default="")
    st_base_src = models.TextField('Keterangan Status Awal', blank=True, default="")
    leave_start = models.DateField('Mulai Cuti (awal)', null=True, blank=True)
    par = models.TextField('Parent ID', blank=True, default="", db_index=True)
    lahir = models.DateField('Tanggal Lahir', null=True, blank=True)
    hp = models.TextField('No. HP Kontak', blank=True, default="")
    kode_in = models.TextField('Kode Kelas (ubah)', blank=True, default="")
    prog_in = models.TextField('Program (ubah)', blank=True, default="")
    level_in = models.TextField('Level (ubah)', blank=True, default="")
    guru_in = models.TextField('Guru (ubah)', blank=True, default="")
    harga_in = models.FloatField('Harga SPP (ubah)', null=True, blank=True)
    sekolah_in = models.TextField('Sekolah (ubah)', blank=True, default="")
    kode_read = models.TextField('Kode Kelas (terbaca)', blank=True, default="")
    sr_src = models.TextField('Student Report (sumber)', blank=True, default="")
    cert_src = models.TextField('Sertifikat (sumber)', blank=True, default="")
    cert_level = models.TextField('Sertifikat Terakhir', blank=True, default="")
    val_status = models.TextField('Validation Status', blank=True, default="")
    val_by = models.TextField('Validator', blank=True, default="")
    val_date = models.TextField('Validation Date', blank=True, default="")
    val_note = models.TextField('Catatan Validator', blank=True, default="")
    sr_detail = models.TextField('Detail Student Report (sumber)', blank=True, default="")
    cert_detail = models.TextField('Detail Sertifikat (sumber)', blank=True, default="")
    prov_file = models.TextField('Source File', blank=True, default="")
    prov_sheet = models.TextField('Source Sheet', blank=True, default="")
    prov_row = models.FloatField('Source Row', null=True, blank=True)
    prov_type = models.TextField('Source Type', blank=True, default="")
    prov_batch = models.TextField('Import Batch', blank=True, default="")
    prov_date = models.DateField('Import Date', null=True, blank=True)

    class Meta(ExcelRow.Meta):
        db_table = "x_student_master"
        verbose_name = 'STUDENT_MASTER'
        verbose_name_plural = 'STUDENT_MASTER'
        constraints = [models.UniqueConstraint(fields=["branch", 'std'], name="uq_student_master_key")]


class StudentIdMapping(ExcelRow):
    EXCEL_SHEET = 'STUDENT_ID_MAPPING'
    EXCEL_KEY = 'map'

    std = models.TextField('Student ID', blank=True, default="", db_index=True)
    code = models.TextField('Kode Kelas', blank=True, default="", db_index=True)
    hasil = models.TextField('Hasil', blank=True, default="")
    ket = models.TextField('Keterangan', blank=True, default="")
    val_status = models.TextField('Validation Status', blank=True, default="")
    val_by = models.TextField('Validator', blank=True, default="")
    val_date = models.TextField('Validation Date', blank=True, default="")
    val_note = models.TextField('Catatan Validator', blank=True, default="")
    map = models.CharField('Mapping ID', max_length=200, db_index=True)
    std_usulan = models.TextField('Student ID (usulan)', blank=True, default="")
    system = models.TextField('Source System', blank=True, default="")
    name = models.TextField('Original Name', blank=True, default="")
    norm = models.TextField('Normalized Name', blank=True, default="")
    status = models.TextField('Match Status', blank=True, default="")
    conf = models.TextField('Matching Confidence', blank=True, default="")
    evidence = models.TextField('Matching Evidence', blank=True, default="")
    ceknama_row = models.FloatField('Baris CEK_NAMA', null=True, blank=True)
    prov_file = models.TextField('Source File', blank=True, default="")
    prov_sheet = models.TextField('Source Sheet', blank=True, default="")
    prov_row = models.FloatField('Source Row', null=True, blank=True)
    prov_type = models.TextField('Source Type', blank=True, default="")
    prov_batch = models.TextField('Import Batch', blank=True, default="")
    prov_date = models.DateField('Import Date', null=True, blank=True)

    class Meta(ExcelRow.Meta):
        db_table = "x_student_id_mapping"
        verbose_name = 'STUDENT_ID_MAPPING'
        verbose_name_plural = 'STUDENT_ID_MAPPING'
        constraints = [models.UniqueConstraint(fields=["branch", 'map'], name="uq_student_id_mapping_key")]


class StudentOff(ExcelRow):
    EXCEL_SHEET = 'STUDENT_OFF'
    EXCEL_KEY = 'off_id'

    nama = models.TextField('Nama Murid', blank=True, default="")
    std = models.TextField('Student ID', blank=True, default="", db_index=True)
    month = models.DateField('Bulan Off', null=True, blank=True)
    tgl = models.DateField('Tanggal Off', null=True, blank=True)
    tgl_text = models.TextField('Tanggal Off (teks asli)', blank=True, default="")
    alasan = models.TextField('Alasan Off', blank=True, default="")
    kode = models.TextField('Kode Kelas Terakhir', blank=True, default="")
    program = models.TextField('Program', blank=True, default="")
    level = models.TextField('Level', blank=True, default="")
    guru = models.TextField('Guru Terakhir', blank=True, default="")
    mode = models.TextField('Mode', blank=True, default="")
    sekolah = models.TextField('Sekolah', blank=True, default="")
    kota = models.TextField('Kota', blank=True, default="")
    last_active = models.DateField('Bulan Aktif Terakhir', null=True, blank=True)
    n_active = models.FloatField('Lama Aktif Sebelum Off (bln)', null=True, blank=True)
    join = models.DateField('Tanggal Join', null=True, blank=True)
    join_text = models.TextField('Tanggal Join (teks asli)', blank=True, default="")
    fu_src = models.TextField('Follow-up di Sumber', blank=True, default="")
    val_status = models.TextField('Validation Status', blank=True, default="")
    val_by = models.TextField('Validator', blank=True, default="")
    val_date = models.TextField('Validation Date', blank=True, default="")
    val_note = models.TextField('Catatan', blank=True, default="")
    off_id = models.CharField('Off Record ID', max_length=200, db_index=True)
    v1 = models.TextField('ID v1', blank=True, default="")
    kode_lain = models.TextField('Kode di Sheet Lain', blank=True, default="")
    tgl_src = models.TextField('Sumber Tanggal Off', blank=True, default="")
    reason_ids = models.TextField('Reason ID', blank=True, default="")
    sumber = models.TextField('Sumber Alasan', blank=True, default="")
    spp = models.TextField('SPP Terakhir', blank=True, default="")
    status_src = models.TextField('Status (riwayat DB Murid)', blank=True, default="")
    kat_in = models.TextField('Kategori (INPUT CENTER)', blank=True, default="")
    prov_file = models.TextField('Source File', blank=True, default="")
    prov_sheet = models.TextField('Source Sheet', blank=True, default="")
    prov_row = models.TextField('Source Row', blank=True, default="")
    prov_type = models.TextField('Source Type', blank=True, default="")
    prov_batch = models.TextField('Import Batch', blank=True, default="")
    prov_date = models.DateField('Import Date', null=True, blank=True)
    s360 = models.TextField('S360', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_student_off"
        verbose_name = 'STUDENT_OFF'
        verbose_name_plural = 'STUDENT_OFF'
        constraints = [models.UniqueConstraint(fields=["branch", 'off_id'], name="uq_student_off_key")]


class StatusEvent(ExcelRow):
    EXCEL_SHEET = 'STATUS_EVENT'
    EXCEL_KEY = 'eid'

    eid = models.CharField('Event ID', max_length=200, db_index=True)
    tgl = models.DateField('Tanggal Efektif', null=True, blank=True)
    std = models.TextField('Student ID', blank=True, default="", db_index=True)
    status = models.TextField('Status Baru', blank=True, default="")
    jenis = models.TextField('Jenis', blank=True, default="")
    alasan = models.TextField('Alasan', blank=True, default="")
    kembali = models.DateField('Perkiraan Kembali', null=True, blank=True)
    konfirm = models.TextField('Dikonfirmasi', blank=True, default="")
    oleh = models.TextField('Diinput Oleh', blank=True, default="")
    pada = models.DateTimeField('Diinput Pada', null=True, blank=True)
    sumber = models.TextField('Sumber', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_status_event"
        verbose_name = 'STATUS_EVENT'
        verbose_name_plural = 'STATUS_EVENT'
        constraints = [models.UniqueConstraint(fields=["branch", 'eid'], name="uq_status_event_key")]


class ParentMaster(ExcelRow):
    EXCEL_SHEET = 'PARENT_MASTER'
    EXCEL_KEY = 'pid'

    pid = models.CharField('Parent ID', max_length=200, db_index=True)
    nama = models.TextField('Nama Orang Tua', blank=True, default="")
    hub = models.TextField('Hubungan', blank=True, default="")
    wa = models.TextField('WhatsApp', blank=True, default="")
    email = models.TextField('Email', blank=True, default="")
    alamat = models.TextField('Alamat', blank=True, default="")
    va = models.TextField('Referensi Pembayaran / VA', blank=True, default="")
    pref = models.TextField('Preferensi Komunikasi', blank=True, default="")
    anak_src = models.TextField('Anak di Sumber', blank=True, default="")
    sumber = models.TextField('Sumber', blank=True, default="")
    catatan = models.TextField('Catatan', blank=True, default="")
    bukti = models.TextField('Bukti', blank=True, default="")
    prov_file = models.TextField('Source File', blank=True, default="")
    prov_sheet = models.TextField('Source Sheet', blank=True, default="")
    prov_row = models.TextField('Source Row', blank=True, default="")
    prov_type = models.TextField('Source Type', blank=True, default="")
    prov_batch = models.TextField('Import Batch', blank=True, default="")
    prov_date = models.DateField('Import Date', null=True, blank=True)

    class Meta(ExcelRow.Meta):
        db_table = "x_parent_master"
        verbose_name = 'PARENT_MASTER'
        verbose_name_plural = 'PARENT_MASTER'
        constraints = [models.UniqueConstraint(fields=["branch", 'pid'], name="uq_parent_master_key")]


class FollowUp(ExcelRow):
    EXCEL_SHEET = 'FOLLOW_UP'
    EXCEL_KEY = 'fid'

    fid = models.CharField('Follow Up ID', max_length=200, db_index=True)
    tgl = models.DateField('Tanggal', null=True, blank=True)
    jenis = models.TextField('Jenis', blank=True, default="")
    std = models.TextField('Student ID', blank=True, default="", db_index=True)
    lead = models.TextField('Lead ID', blank=True, default="", db_index=True)
    pic = models.TextField('PIC', blank=True, default="")
    status = models.TextField('Status', blank=True, default="")
    aksi = models.TextField('Tindak Lanjut', blank=True, default="")
    catatan = models.TextField('Catatan / Hasil', blank=True, default="")
    next = models.DateField('Tgl Berikutnya', null=True, blank=True)
    oleh = models.TextField('Diinput Oleh', blank=True, default="")
    pada = models.DateTimeField('Diinput Pada', null=True, blank=True)
    sumber = models.TextField('Sumber', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_follow_up"
        verbose_name = 'FOLLOW_UP'
        verbose_name_plural = 'FOLLOW_UP'
        constraints = [models.UniqueConstraint(fields=["branch", 'fid'], name="uq_follow_up_key")]


class AcademicRecord(ExcelRow):
    EXCEL_SHEET = 'ACADEMIC_RECORD'
    EXCEL_KEY = 'aid'

    aid = models.CharField('Record ID', max_length=200, db_index=True)
    tgl = models.DateField('Tanggal', null=True, blank=True)
    std = models.TextField('Student ID', blank=True, default="", db_index=True)
    pct = models.FloatField('Progres (%)', null=True, blank=True)
    kes = models.TextField('Kesimpulan', blank=True, default="")
    sr = models.TextField('Student Report', blank=True, default="")
    sr_link = models.TextField('Link Student Report', blank=True, default="")
    cert = models.TextField('Sertifikat', blank=True, default="")
    cert_link = models.TextField('Link Sertifikat', blank=True, default="")
    cat = models.TextField('Catatan Akademik', blank=True, default="")
    rekom = models.TextField('Rekomendasi', blank=True, default="")
    oleh = models.TextField('Diinput Oleh', blank=True, default="")
    pada = models.DateTimeField('Diinput Pada', null=True, blank=True)
    sumber = models.TextField('Sumber', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_academic_record"
        verbose_name = 'ACADEMIC_RECORD'
        verbose_name_plural = 'ACADEMIC_RECORD'
        constraints = [models.UniqueConstraint(fields=["branch", 'aid'], name="uq_academic_record_key")]


class Lead(ExcelRow):
    EXCEL_SHEET = 'LEAD'
    EXCEL_KEY = 'lid'

    lid = models.CharField('Lead ID', max_length=200, db_index=True)
    tgl = models.DateField('Tanggal Masuk', null=True, blank=True)
    anak = models.TextField('Nama Anak', blank=True, default="")
    ortu = models.TextField('Nama Orang Tua', blank=True, default="")
    wa = models.TextField('WhatsApp', blank=True, default="")
    email = models.TextField('Email', blank=True, default="")
    sekolah = models.TextField('Sekolah', blank=True, default="")
    minat = models.TextField('Minat Program', blank=True, default="")
    sumber = models.TextField('Sumber', blank=True, default="")
    status = models.TextField('Status', blank=True, default="")
    trial = models.DateField('Tgl Trial', null=True, blank=True)
    hasil = models.TextField('Hasil Trial', blank=True, default="")
    lost = models.TextField('Alasan Tidak Lanjut', blank=True, default="")
    std = models.TextField('Student ID (konversi)', blank=True, default="", db_index=True)
    pic = models.TextField('PIC', blank=True, default="")
    catatan = models.TextField('Catatan', blank=True, default="")
    ubah = models.DateTimeField('Terakhir Diubah', null=True, blank=True)
    oleh = models.TextField('Diinput Oleh', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_lead"
        verbose_name = 'LEAD'
        verbose_name_plural = 'LEAD'
        constraints = [models.UniqueConstraint(fields=["branch", 'lid'], name="uq_lead_key")]


class Dokumen(ExcelRow):
    EXCEL_SHEET = 'DOKUMEN'
    EXCEL_KEY = 'did'

    did = models.CharField('Dokumen ID', max_length=200, db_index=True)
    tgl = models.DateField('Tanggal', null=True, blank=True)
    std = models.TextField('Student ID', blank=True, default="", db_index=True)
    jenis = models.TextField('Jenis Dokumen', blank=True, default="")
    status = models.TextField('Status', blank=True, default="")
    link = models.TextField('Link / Lokasi File', blank=True, default="")
    catatan = models.TextField('Catatan', blank=True, default="")
    oleh = models.TextField('Diinput Oleh', blank=True, default="")
    pada = models.DateTimeField('Diinput Pada', null=True, blank=True)

    class Meta(ExcelRow.Meta):
        db_table = "x_dokumen"
        verbose_name = 'DOKUMEN'
        verbose_name_plural = 'DOKUMEN'
        constraints = [models.UniqueConstraint(fields=["branch", 'did'], name="uq_dokumen_key")]


class DBulan(ExcelRow):
    EXCEL_SHEET = 'D_BULAN'
    EXCEL_KEY = 'key'

    key = models.CharField('Kunci (ID|yyyymm)', max_length=200, db_index=True)
    v1 = models.TextField('ID', blank=True, default="")
    nama = models.TextField('Nama Murid', blank=True, default="")
    bulan = models.DateField('Bulan', null=True, blank=True)
    status = models.TextField('Status', blank=True, default="")
    tgl_status = models.DateField('Tanggal status', null=True, blank=True)
    tgl_status_text = models.TextField('Tanggal status (teks asli)', blank=True, default="")
    ket = models.TextField('Keterangan', blank=True, default="")
    grade = models.TextField('Level (Grade)', blank=True, default="")
    guru_asli = models.TextField('Guru (asli)', blank=True, default="")
    guru = models.TextField('Guru (rapi)', blank=True, default="")
    tipe = models.TextField('Tipe Kelas', blank=True, default="")
    mode = models.TextField('Mode', blank=True, default="")
    sumber = models.TextField('Sumber (sel asli)', blank=True, default="")
    std = models.TextField('Student ID', blank=True, default="", db_index=True)
    kode_bulan = models.TextField('Kode Kelas (bulan itu)', blank=True, default="")
    kode_terakhir = models.TextField('Kode Kelas (terakhir, DB Murid)', blank=True, default="")
    kode_sumber = models.TextField('Sumber Kode Kelas', blank=True, default="")
    sekolah = models.TextField('Sekolah', blank=True, default="")
    batch = models.TextField('Import Batch', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_d_bulan"
        verbose_name = 'D_BULAN'
        verbose_name_plural = 'D_BULAN'
        constraints = [models.UniqueConstraint(fields=["branch", 'key'], name="uq_d_bulan_key")]


class DMurid(ExcelRow):
    EXCEL_SHEET = 'D_MURID'
    EXCEL_KEY = 'v1'

    v1 = models.CharField('ID', max_length=200, db_index=True)
    nama = models.TextField('Nama Murid', blank=True, default="")
    nama_persis_seperti_di_sumber = models.TextField('Nama (persis seperti di sumber)', blank=True, default="")
    baris_di_db_murid_jkt = models.FloatField('Baris di DB Murid JKT', null=True, blank=True)
    kode_kelas = models.TextField('Kode Kelas', blank=True, default="", db_index=True)
    tipe_kelas_rapi = models.TextField('Tipe Kelas (rapi)', blank=True, default="")
    tipe_kelas_asli = models.TextField('Tipe Kelas (asli)', blank=True, default="")
    kelompok_usia = models.TextField('Kelompok Usia', blank=True, default="")
    mode_rapi = models.TextField('Mode (rapi)', blank=True, default="")
    mode_asli = models.TextField('Mode (asli)', blank=True, default="")
    kota = models.TextField('Kota', blank=True, default="")
    pembagian = models.TextField('Pembagian', blank=True, default="")
    nama_sekolah = models.TextField('Nama Sekolah', blank=True, default="")
    join_tanggal = models.DateField('Join (tanggal)', null=True, blank=True)
    join_teks_asli_kolom_l = models.TextField('Join (teks asli, kolom L)', blank=True, default="")
    join_kolom_m_bila_bukan_tanggal = models.TextField('Join (kolom M bila bukan tanggal)', blank=True, default="")
    harga_spp_angka = models.FloatField('Harga SPP (angka)', null=True, blank=True)
    harga_spp_teks_asli_bila_bukan_angka = models.TextField('Harga SPP (teks asli bila bukan angka)', blank=True, default="")
    std = models.TextField('Student ID', blank=True, default="", db_index=True)
    status_kode_kelas = models.TextField('Status Kode Kelas', blank=True, default="")
    kode_kelas_terbaca = models.TextField('Kode Kelas Terbaca', blank=True, default="")
    kode_kelas_bukti_lain = models.TextField('Kode Kelas Bukti Lain', blank=True, default="")
    unit_id = models.TextField('Unit ID', blank=True, default="")
    bahasa_dari_kode = models.TextField('Bahasa (dari kode)', blank=True, default="")
    kode_kelas_dipakai = models.TextField('Kode Kelas (dipakai)', blank=True, default="")
    arti_kode_kelas = models.TextField('Arti Kode Kelas', blank=True, default="")
    keterangan_kode_kelas = models.TextField('Keterangan Kode Kelas', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_d_murid"
        verbose_name = 'D_MURID'
        verbose_name_plural = 'D_MURID'
        constraints = [models.UniqueConstraint(fields=["branch", 'v1'], name="uq_d_murid_key")]
