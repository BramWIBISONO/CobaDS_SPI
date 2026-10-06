from django.conf import settings
from django.db import models

RUBRIK = [("nilai_konsep", "Pemahaman konsep"), ("nilai_logika", "Logika & problem solving"),
          ("nilai_kreativitas", "Kreativitas & kualitas project"), ("nilai_presentasi", "Presentasi & komunikasi")]
LULUS_MIN = 70                       # rata-rata rubrik minimal untuk bisa disetujui (kebijakan akademik - ubah di sini)


def predikat(rata):
    if rata is None:
        return ""
    return "Sangat Baik" if rata >= 90 else "Baik" if rata >= 80 else "Cukup" if rata >= LULUS_MIN else "Perlu bimbingan"


class FinalProject(models.Model):
    """Final project murid di akhir satu level. Disetujui Manager / Branch Admin -> sertifikat + Student Report otomatis."""
    DIAJUKAN, DISETUJUI, DITOLAK = "DIAJUKAN", "DISETUJUI", "DITOLAK"
    STATUS = [(DIAJUKAN, "Menunggu persetujuan"), (DISETUJUI, "Disetujui"), (DITOLAK, "Ditolak")]

    branch = models.ForeignKey("branches.Branch", on_delete=models.CASCADE, related_name="+")
    std = models.CharField("Student ID", max_length=40, db_index=True)
    nama = models.CharField("Nama murid (saat diajukan)", max_length=200)
    level = models.CharField("Level", max_length=80)
    kode_level = models.CharField("Kode level", max_length=10, blank=True, default="")
    kode_kelas = models.CharField("Kode kelas", max_length=60, blank=True, default="")
    guru = models.CharField("Guru", max_length=120, blank=True, default="")
    judul = models.CharField("Judul project", max_length=200)
    deskripsi = models.TextField("Deskripsi project", blank=True, default="")
    link = models.URLField("Link project", max_length=500, blank=True, default="")
    tgl_selesai = models.DateField("Tanggal presentasi / selesai")
    nilai_konsep = models.PositiveSmallIntegerField("Pemahaman konsep")
    nilai_logika = models.PositiveSmallIntegerField("Logika & problem solving")
    nilai_kreativitas = models.PositiveSmallIntegerField("Kreativitas & kualitas project")
    nilai_presentasi = models.PositiveSmallIntegerField("Presentasi & komunikasi")
    kekuatan = models.TextField("Kekuatan murid", blank=True, default="")
    perlu_ditingkatkan = models.TextField("Yang perlu ditingkatkan", blank=True, default="")
    catatan = models.TextField("Catatan guru untuk orang tua", blank=True, default="")
    rekomendasi = models.CharField("Rekomendasi level berikutnya", max_length=80, blank=True, default="")
    status = models.CharField("Status", max_length=10, choices=STATUS, default=DIAJUKAN, db_index=True)
    diajukan_oleh = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    diajukan_pada = models.DateTimeField(auto_now_add=True)
    diputuskan_oleh = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    diputuskan_pada = models.DateTimeField(null=True, blank=True)
    alasan_tolak = models.TextField("Alasan ditolak", blank=True, default="")
    cert_no = models.CharField("Nomor sertifikat", max_length=40, blank=True, default="", db_index=True)
    cert_tgl = models.DateField("Tanggal sertifikat", null=True, blank=True)
    cert_png = models.CharField(max_length=300, blank=True, default="")
    cert_pdf = models.CharField(max_length=300, blank=True, default="")
    cert_preview = models.CharField(max_length=300, blank=True, default="")
    aid = models.CharField("Record ID akademik", max_length=40, blank=True, default="")

    class Meta:
        ordering = ["-diajukan_pada"]
        verbose_name = "Final project"
        constraints = [models.UniqueConstraint(fields=["branch", "cert_no"], condition=~models.Q(cert_no=""), name="uq_final_project_cert_no")]

    def __str__(self):
        return f"{self.std} {self.level} {self.status}"

    @property
    def nilai(self):
        return [(label, getattr(self, f)) for f, label in RUBRIK]

    @property
    def rata(self):
        vals = [v for _l, v in self.nilai if v is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    @property
    def predikat(self):
        return predikat(self.rata)

    @property
    def lulus(self):
        return self.rata is not None and self.rata >= LULUS_MIN

    @property
    def ada_sertifikat(self):
        return bool(self.cert_png)
