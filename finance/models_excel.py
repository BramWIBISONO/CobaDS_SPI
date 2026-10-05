# DIBANGKITKAN oleh tools/generate_models.py dari importer/schema/excel_tables.json - jangan diedit tangan.
# Satu model per tabel Excel v4; kolom FORMULA tidak disimpan (dihitung oleh service).
from django.db import models

from core.models import ExcelRow

__all__ = ['BukuKas', 'Pembayar', 'NotaLog', 'Periode', 'SppTagihan', 'BuktiBayar', 'BukuKasKeluar']


class BukuKas(ExcelRow):
    EXCEL_SHEET = 'BUKU_KAS'
    EXCEL_KEY = 'lid'

    bulan = models.DateField('Bulan', null=True, blank=True)
    tgl = models.DateField('Tanggal', null=True, blank=True)
    ket = models.TextField('Keterangan', blank=True, default="")
    kode = models.TextField('Kode Akun', blank=True, default="")
    jenis = models.TextField('Jenis', blank=True, default="")
    nominal = models.FloatField('Nominal (Rp)', null=True, blank=True)
    murid_sys = models.TextField('Murid (hasil sistem)', blank=True, default="")
    yakin = models.TextField('Keyakinan', blank=True, default="")
    kor1 = models.TextField('Murid (koreksi)', blank=True, default="")
    kor2 = models.TextField('Murid kedua (koreksi)', blank=True, default="")
    catatan = models.TextField('Catatan', blank=True, default="")
    dihitung = models.TextField('Dihitung', blank=True, default="")
    per_sys = models.TextField('Periode Tagihan (sistem)', blank=True, default="")
    per_in = models.TextField('Periode Tagihan (koreksi)', blank=True, default="")
    per_note = models.TextField('Catatan Periode', blank=True, default="")
    lid = models.CharField('ID Baris', max_length=200, db_index=True)
    versi = models.TextField('Versi Jurnal', blank=True, default="")
    nama_siswa = models.TextField('Nama Siswa (kolom jurnal)', blank=True, default="")
    bukti = models.TextField('Bukti Transfer', blank=True, default="")
    ket_bank = models.TextField('Keterangan Bank', blank=True, default="")
    entitas = models.TextField('Entitas / Kanal', blank=True, default="")
    linked_by = models.TextField('Dasar Tautan', blank=True, default="")
    note = models.TextField('Catatan Pencocokan', blank=True, default="")
    cands = models.TextField('Kandidat Lain', blank=True, default="")
    bln_teks = models.TextField('Bulan di Keterangan', blank=True, default="")
    ss1 = models.TextField('Student ID sistem 1', blank=True, default="")
    ss2 = models.TextField('Student ID sistem 2', blank=True, default="")
    ss3 = models.TextField('Student ID sistem 3', blank=True, default="")
    ss4 = models.TextField('Student ID sistem 4', blank=True, default="")
    sb1 = models.FloatField('Bagian sistem 1 (Rp)', null=True, blank=True)
    sb2 = models.FloatField('Bagian sistem 2 (Rp)', null=True, blank=True)
    sb3 = models.FloatField('Bagian sistem 3 (Rp)', null=True, blank=True)
    sb4 = models.FloatField('Bagian sistem 4 (Rp)', null=True, blank=True)
    prov_file = models.TextField('Source File', blank=True, default="")
    prov_sheet = models.TextField('Source Sheet', blank=True, default="")
    prov_row = models.FloatField('Source Row', null=True, blank=True)
    prov_type = models.TextField('Source Type', blank=True, default="")
    prov_batch = models.TextField('Import Batch', blank=True, default="")
    prov_date = models.DateField('Import Date', null=True, blank=True)

    class Meta(ExcelRow.Meta):
        db_table = "x_buku_kas"
        verbose_name = 'BUKU_KAS'
        verbose_name_plural = 'BUKU_KAS'
        constraints = [models.UniqueConstraint(fields=["branch", 'lid'], name="uq_buku_kas_key")]


class Pembayar(ExcelRow):
    EXCEL_SHEET = 'PEMBAYAR'
    EXCEL_KEY = 'pid'

    payer = models.TextField('Nama Pembayar', blank=True, default="")
    murid_src = models.TextField('Nama Murid (sumber)', blank=True, default="")
    murid_sys = models.TextField('Murid (hasil sistem)', blank=True, default="")
    yakin = models.TextField('Keyakinan', blank=True, default="")
    kor = models.TextField('Murid (koreksi)', blank=True, default="")
    pid = models.CharField('Payer ID', max_length=200, db_index=True)
    std_sys = models.TextField('Student ID (sistem)', blank=True, default="")
    cands = models.TextField('Kandidat', blank=True, default="")
    prov_file = models.TextField('Source File', blank=True, default="")
    prov_sheet = models.TextField('Source Sheet', blank=True, default="")
    prov_row = models.FloatField('Source Row', null=True, blank=True)
    prov_type = models.TextField('Source Type', blank=True, default="")
    prov_batch = models.TextField('Import Batch', blank=True, default="")
    prov_date = models.DateField('Import Date', null=True, blank=True)

    class Meta(ExcelRow.Meta):
        db_table = "x_pembayar"
        verbose_name = 'PEMBAYAR'
        verbose_name_plural = 'PEMBAYAR'
        constraints = [models.UniqueConstraint(fields=["branch", 'pid'], name="uq_pembayar_key")]


class NotaLog(ExcelRow):
    EXCEL_SHEET = 'NOTA_LOG'
    EXCEL_KEY = 'no'

    no = models.CharField('Nomor Nota', max_length=200, db_index=True)
    tgl = models.DateTimeField('Tanggal Dibuat', null=True, blank=True)
    std = models.TextField('Student ID', blank=True, default="", db_index=True)
    nama = models.TextField('Nama Murid', blank=True, default="")
    periode = models.TextField('Periode', blank=True, default="", db_index=True)
    kepada = models.TextField('Kepada', blank=True, default="")
    tagihan = models.FloatField('Tagihan (Rp)', null=True, blank=True)
    bayar = models.FloatField('Terbayar di Buku Kas (Rp)', null=True, blank=True)
    status = models.TextField('Status', blank=True, default="")
    file = models.TextField('File PDF', blank=True, default="")
    user = models.TextField('Dibuat Oleh', blank=True, default="")
    catatan = models.TextField('Catatan', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_nota_log"
        verbose_name = 'NOTA_LOG'
        verbose_name_plural = 'NOTA_LOG'
        constraints = [models.UniqueConstraint(fields=["branch", 'no'], name="uq_nota_log_key")]


class Periode(ExcelRow):
    EXCEL_SHEET = 'PERIODE'
    EXCEL_KEY = 'per'

    per = models.CharField('Periode', max_length=200, db_index=True)
    label = models.TextField('Label', blank=True, default="")
    mulai = models.DateField('Mulai', null=True, blank=True)
    akhir = models.DateField('Akhir', null=True, blank=True)
    status = models.TextField('Status', blank=True, default="")
    buka = models.DateTimeField('Dibuka Pada', null=True, blank=True)
    buka_oleh = models.TextField('Dibuka Oleh', blank=True, default="")
    tutup = models.DateTimeField('Ditutup Pada', null=True, blank=True)
    tutup_oleh = models.TextField('Ditutup Oleh', blank=True, default="")
    cat = models.TextField('Catatan Penutupan', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_periode"
        verbose_name = 'PERIODE'
        verbose_name_plural = 'PERIODE'
        constraints = [models.UniqueConstraint(fields=["branch", 'per'], name="uq_periode_key")]


class SppTagihan(ExcelRow):
    EXCEL_SHEET = 'SPP_TAGIHAN'
    EXCEL_KEY = 'tid'

    tid = models.CharField('Tagihan ID', max_length=200, db_index=True)
    per = models.TextField('Periode', blank=True, default="", db_index=True)
    std = models.TextField('Student ID', blank=True, default="", db_index=True)
    st = models.TextField('Status Murid saat Ditagih', blank=True, default="")
    harga = models.DecimalField('Harga SPP', max_digits=14, decimal_places=2, null=True, blank=True)
    diskon = models.DecimalField('Diskon', max_digits=14, decimal_places=2, null=True, blank=True)
    adj = models.DecimalField('Penyesuaian', max_digits=14, decimal_places=2, null=True, blank=True)
    keputusan = models.TextField('Keputusan', blank=True, default="")
    catatan = models.TextField('Catatan', blank=True, default="")
    pada = models.DateTimeField('Dibuat Pada', null=True, blank=True)
    oleh = models.TextField('Dibuat Oleh', blank=True, default="")
    sumber = models.TextField('Sumber', blank=True, default="")

    class Meta(ExcelRow.Meta):
        db_table = "x_spp_tagihan"
        verbose_name = 'SPP_TAGIHAN'
        verbose_name_plural = 'SPP_TAGIHAN'
        constraints = [models.UniqueConstraint(fields=["branch", 'tid'], name="uq_spp_tagihan_key")]


class BuktiBayar(ExcelRow):
    EXCEL_SHEET = 'BUKTI_BAYAR'
    EXCEL_KEY = 'bid'

    bid = models.CharField('Pembayaran ID', max_length=200, db_index=True)
    pada = models.DateTimeField('Diinput Pada', null=True, blank=True)
    std = models.TextField('Student ID', blank=True, default="", db_index=True)
    per = models.TextField('Periode Tagihan', blank=True, default="")
    nominal = models.DecimalField('Nominal', max_digits=14, decimal_places=2, null=True, blank=True)
    tgl = models.DateField('Tanggal Bayar', null=True, blank=True)
    metode = models.TextField('Metode', blank=True, default="")
    bukti = models.TextField('Bukti Transfer', blank=True, default="")
    ref = models.TextField('Referensi', blank=True, default="")
    ver = models.TextField('Status Verifikasi', blank=True, default="")
    catatan = models.TextField('Catatan', blank=True, default="")
    oleh = models.TextField('Diinput Oleh', blank=True, default="")
    ver_oleh = models.TextField('Diverifikasi Oleh', blank=True, default="")
    ver_pada = models.DateTimeField('Diverifikasi Pada', null=True, blank=True)

    class Meta(ExcelRow.Meta):
        db_table = "x_bukti_bayar"
        verbose_name = 'BUKTI_BAYAR'
        verbose_name_plural = 'BUKTI_BAYAR'
        constraints = [models.UniqueConstraint(fields=["branch", 'bid'], name="uq_bukti_bayar_key")]


class BukuKasKeluar(ExcelRow):
    EXCEL_SHEET = 'BUKU_KAS_KELUAR'
    EXCEL_KEY = 'lid'

    bulan = models.DateField('Bulan', null=True, blank=True)
    tgl = models.DateField('Tanggal', null=True, blank=True)
    ket = models.TextField('Keterangan', blank=True, default="")
    kode = models.TextField('Kode Akun', blank=True, default="")
    kel = models.TextField('Kelompok', blank=True, default="")
    nominal = models.FloatField('Nominal (Rp)', null=True, blank=True)
    entitas = models.TextField('Entitas / Kanal', blank=True, default="")
    lid = models.CharField('ID Baris', max_length=200, db_index=True)
    prov_file = models.TextField('Source File', blank=True, default="")
    prov_sheet = models.TextField('Source Sheet', blank=True, default="")
    prov_row = models.FloatField('Source Row', null=True, blank=True)
    prov_type = models.TextField('Source Type', blank=True, default="")
    prov_batch = models.TextField('Import Batch', blank=True, default="")
    prov_date = models.DateField('Import Date', null=True, blank=True)

    class Meta(ExcelRow.Meta):
        db_table = "x_buku_kas_keluar"
        verbose_name = 'BUKU_KAS_KELUAR'
        verbose_name_plural = 'BUKU_KAS_KELUAR'
        constraints = [models.UniqueConstraint(fields=["branch", 'lid'], name="uq_buku_kas_keluar_key")]
