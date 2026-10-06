"""Final project -> persetujuan -> sertifikat + Student Report + catatan akademik. Semua perubahan lewat sini (diaudit)."""
import re

from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from branches.models import Branch
from core import audit
from core.ids import next_id, next_row_no
from dashboards.calc.base import fold
from dashboards.calc.status import guru_dipakai, kode_dipakai
from masterdata.models import ProgramMaster
from students.models import AcademicRecord, StudentMaster
from students.services import change_program, get_student

from . import certificates
from .models import LULUS_MIN, RUBRIK, FinalProject

NOMOR = re.compile(r"SPI(\d{2})-(\d{4})(\d{3,})")


def kode_level(level):
    m = re.search(r"(\d+\.\d+)", level or "")
    return m.group(1) if m else ""


def level_dipakai(student):
    return (student.level_in or student.level or "").strip()


def program_dari_level(branch, level):
    row = ProgramMaster.objects.for_branch(branch).filter(level__iexact=level).first()
    return row.program if row else (level.split(" ")[0] if level else "")


def level_berikutnya(branch, level):
    """Level sesudahnya menurut urutan PROGRAM_MASTER (Foundation 1.0 → 1.1 → 1.2 → Development 2.0 → ...)."""
    levels = [lv for lv in ProgramMaster.objects.for_branch(branch).order_by("row_no").values_list("level", flat=True) if lv]
    folded = [fold(x) for x in levels]
    if fold(level) in folded:
        i = folded.index(fold(level))
        return levels[i + 1] if i + 1 < len(levels) else ""
    return ""


def nomor_berikutnya(branch, kode, tahun):
    """SPI{level}-{tahun}{urut 3 digit}: lanjut dari nomor tertinggi yang pernah terbit (aplikasi + riwayat sertifikat Excel)."""
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("nomor_berikutnya() harus di dalam transaction.atomic()")
    list(Branch.objects.select_for_update().filter(pk=branch.pk).values_list("pk", flat=True))
    lv = kode.replace(".", "")
    top = 0
    teks = list(FinalProject.objects.filter(branch=branch).exclude(cert_no="").values_list("cert_no", flat=True))
    for a, b, c in StudentMaster.objects.for_branch(branch).values_list("cert_level", "cert_detail", "cert_src"):
        teks.extend((a or "", b or "", c or ""))
    teks.extend(AcademicRecord.objects.for_branch(branch).values_list("cert", flat=True))
    for t in teks:
        for m in NOMOR.finditer(t or ""):
            if m.group(1) == lv and int(m.group(2)) == tahun:
                top = max(top, int(m.group(3)))
    return f"SPI{lv}-{tahun}{top + 1:03d}"


def _nilai(v, label):
    try:
        n = int(v)
    except (TypeError, ValueError):
        raise ValidationError(f"Nilai {label} harus angka 0-100.")
    if not 0 <= n <= 100:
        raise ValidationError(f"Nilai {label} harus 0-100.")
    return n


@transaction.atomic
def ajukan(branch, user, std, *, judul, tgl_selesai, deskripsi="", link="", kekuatan="", perlu_ditingkatkan="", catatan="", rekomendasi="",
           level="", **nilai):
    student = get_student(branch, std)
    level = (level or level_dipakai(student)).strip()
    if not level:
        raise ValidationError("Level murid belum tercatat - isi program & level di profil murid dulu.")
    if not (judul or "").strip():
        raise ValidationError("Judul project wajib diisi.")
    if FinalProject.objects.filter(branch=branch, std=std, level__iexact=level, status__in=[FinalProject.DIAJUKAN, FinalProject.DISETUJUI]).exists():
        raise ValidationError(f"Final project {level} murid ini sudah diajukan / disetujui.")
    p = FinalProject.objects.create(
        branch=branch, std=std, nama=student.nama or std, level=level, kode_level=kode_level(level), kode_kelas=kode_dipakai(student),
        guru=guru_dipakai(student), judul=judul.strip(), deskripsi=deskripsi.strip(), link=(link or "").strip(), tgl_selesai=tgl_selesai,
        kekuatan=kekuatan.strip(), perlu_ditingkatkan=perlu_ditingkatkan.strip(), catatan=catatan.strip(),
        rekomendasi=(rekomendasi or level_berikutnya(branch, level)).strip(), diajukan_oleh=user,
        **{f: _nilai(nilai.get(f), label) for f, label in RUBRIK})
    audit.log(branch=branch, user=user, action="CREATE", entity="FINAL_PROJECT", entity_id=f"FP-{p.pk}", field="Final project",
              new=f"{std} {level} '{p.judul}' rata-rata {p.rata}")
    return p


def _pending(branch, pk):
    p = FinalProject.objects.select_for_update().filter(branch=branch, pk=pk).first()
    if p is None:
        raise ValidationError("Final project tidak ditemukan di cabang ini.")
    if p.status != FinalProject.DIAJUKAN:
        raise ValidationError(f"Final project ini sudah {p.get_status_display().lower()}.")
    return p


@transaction.atomic
def setujui(branch, user, pk, *, naik_level=False, today=None):
    """Setujui: nomor sertifikat, file sertifikat (bila template level ada), catatan AKADEMIK, Sertifikat Terakhir murid, audit."""
    p = _pending(branch, pk)
    if not p.lulus:
        raise ValidationError(f"Rata-rata rubrik {p.rata} di bawah batas lulus {LULUS_MIN} - tolak atau minta perbaikan nilai.")
    today = today or timezone.localdate()
    p.cert_no = nomor_berikutnya(branch, p.kode_level or "00", today.year)
    p.cert_tgl = today
    if certificates.template_for(p.kode_level):
        img = certificates.render(p.kode_level, p.nama, p.cert_no, today)
        files = certificates.simpan(img, f"sertifikat/{branch.code}", p.cert_no)
        p.cert_png, p.cert_pdf, p.cert_preview = files["png"], files["pdf"], files["preview"]
    p.status, p.diputuskan_oleh, p.diputuskan_pada = FinalProject.DISETUJUI, user, timezone.now()
    p.aid = next_id(AcademicRecord, "aid", "AKD-", 6, branch)
    p.save()
    rapor = reverse("akademik:rapor", args=[p.pk])
    AcademicRecord.objects.create(
        branch=branch, row_no=next_row_no(AcademicRecord, branch), aid=p.aid, tgl=p.tgl_selesai, std=p.std, pct=100,
        kes=f"LULUS {p.level} · rata-rata {p.rata} ({p.predikat})", sr="Dibuat otomatis", sr_link=rapor,
        cert=f"{p.level} · {p.cert_no}" + ("" if p.cert_png else " · template belum tersedia"),
        cert_link=reverse("akademik:sertifikat", args=[p.pk, "pdf"]) if p.cert_pdf else "",
        cat=p.catatan, rekom=p.rekomendasi, oleh=user.display_name, pada=timezone.now(), sumber="APLIKASI · Final project")
    s = get_student(branch, p.std)
    lama = s.cert_level
    s.cert_level, s.cert_src = f"{p.level} · {p.cert_no} · {today:%Y-%m-%d}", "Sudah"
    s.save(update_fields=["cert_level", "cert_src"])
    audit.log(branch=branch, user=user, action="UPDATE", entity="FINAL_PROJECT", entity_id=f"FP-{p.pk}", field="Disetujui",
              old="DIAJUKAN", new=f"DISETUJUI · sertifikat {p.cert_no}")
    audit.log(branch=branch, user=user, action="UPDATE", entity="STUDENT_MASTER", entity_id=p.std, field="Sertifikat Terakhir",
              old=lama, new=s.cert_level)
    if naik_level and p.rekomendasi:
        change_program(branch, user, p.std, program=program_dari_level(branch, p.rekomendasi), level=p.rekomendasi)
    return p


@transaction.atomic
def tolak(branch, user, pk, *, alasan):
    p = _pending(branch, pk)
    alasan = (alasan or "").strip()
    if not alasan:
        raise ValidationError("Tulis alasan penolakan agar guru bisa memperbaiki.")
    p.status, p.alasan_tolak, p.diputuskan_oleh, p.diputuskan_pada = FinalProject.DITOLAK, alasan, user, timezone.now()
    p.save()
    audit.log(branch=branch, user=user, action="UPDATE", entity="FINAL_PROJECT", entity_id=f"FP-{p.pk}", field="Ditolak", old="DIAJUKAN", new=alasan)
    return p


def buat_ulang_sertifikat(branch, user, pk):
    """Untuk final project disetujui tanpa file (template baru ditambahkan belakangan): pakai nomor & tanggal yang sama."""
    p = FinalProject.objects.get(branch=branch, pk=pk, status=FinalProject.DISETUJUI)
    img = certificates.render(p.kode_level, p.nama, p.cert_no, p.cert_tgl)
    files = certificates.simpan(img, f"sertifikat/{branch.code}", p.cert_no)
    p.cert_png, p.cert_pdf, p.cert_preview = files["png"], files["pdf"], files["preview"]
    p.save(update_fields=["cert_png", "cert_pdf", "cert_preview"])
    with transaction.atomic():
        audit.log(branch=branch, user=user, action="UPDATE", entity="FINAL_PROJECT", entity_id=f"FP-{p.pk}", field="Sertifikat dibuat", new=p.cert_no)
    return p
