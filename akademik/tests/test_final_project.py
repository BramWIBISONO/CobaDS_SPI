"""Final project -> persetujuan -> sertifikat (nomor SPI, file dari template) + Student Report + catatan akademik."""
import datetime
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse
from PIL import Image

from akademik import certificates, services
from akademik.models import FinalProject
from audit.models import AuditLog
from dashboards.tests.helpers import make_rows
from masterdata.models import ProgramMaster
from students.models import AcademicRecord, StudentMaster

NILAI = {"nilai_konsep": 88, "nilai_logika": 90, "nilai_kreativitas": 85, "nilai_presentasi": 82}
TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "sertif"


@pytest.fixture
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    return settings.MEDIA_ROOT


@pytest.fixture
def jkt(branch, other_branch, media):
    make_rows(ProgramMaster, branch, *[{"pid": f"P{i}", "program": lv.split()[0], "level": lv, "status": "ACTIVE"}
                                      for i, lv in enumerate(["Foundation 1.0", "Foundation 1.1", "Foundation 1.2", "Development 2.0",
                                                              "Development 2.1", "Development 2.2"])])
    make_rows(StudentMaster, branch,
              {"std": "STD-000001", "v1": "M1", "nama": "Alberto Jayaharto", "program": "Development", "level": "Development 2.1",
               "kode_in": "P001", "guru_in": "Mr. Bram", "st_base": "ACTIVE",
               "cert_detail": "Development 2.1: E-sertifikat Dikirim (SPI21-2026007)"},
              {"std": "STD-000002", "v1": "M2", "nama": "Bella Foundation", "program": "Foundation", "level": "Foundation 1.2", "st_base": "ACTIVE"})
    make_rows(StudentMaster, other_branch, {"std": "STD-000009", "nama": "Murid Cabang Lain", "level": "Development 2.1"})
    return branch


def _ajukan(branch, user, std="STD-000001", **kw):
    return services.ajukan(branch, user, std, judul="Game Kejar Bintang", tgl_selesai=datetime.date(2026, 10, 3), **{**NILAI, **kw})


def test_level_helpers():
    assert services.kode_level("Development 2.1") == "2.1" and services.kode_level("Foundation 1.0") == "1.0" and services.kode_level("") == ""


@pytest.mark.django_db
def test_next_level_follows_program_master(jkt):
    assert services.level_berikutnya(jkt, "Foundation 1.2") == "Development 2.0"
    assert services.level_berikutnya(jkt, "Development 2.1") == "Development 2.2"
    assert services.level_berikutnya(jkt, "Development 2.2") == ""


@pytest.mark.django_db
def test_certificate_number_continues_existing_series(jkt, make_user):
    from django.db import transaction
    with transaction.atomic():
        assert services.nomor_berikutnya(jkt, "2.1", 2026) == "SPI21-2026008"        # sesudah SPI21-2026007 dari riwayat Excel
        assert services.nomor_berikutnya(jkt, "1.2", 2026) == "SPI12-2026001"
        assert services.nomor_berikutnya(jkt, "2.1", 2027) == "SPI21-2027001"


@pytest.mark.django_db
@pytest.mark.skipif(not (TEMPLATE_DIR / "2.1 Python.pptx").exists(), reason="template sertifikat tidak ada di mesin ini")
def test_approval_creates_certificate_report_and_records(jkt, make_user, media):
    academic = make_user("akd@spi.test", role="ACADEMIC", branch=jkt)
    manager = make_user("mgr@spi.test", role="MANAGER", branch=jkt)
    p = _ajukan(jkt, academic)
    assert p.status == "DIAJUKAN" and p.rata == 86.2 and p.predikat == "Baik" and p.rekomendasi == "Development 2.2"
    p = services.setujui(jkt, manager, p.pk, naik_level=True, today=datetime.date(2026, 10, 6))
    assert p.status == "DISETUJUI" and p.cert_no == "SPI21-2026008"
    png = Path(media) / p.cert_png
    assert png.exists() and (Path(media) / p.cert_pdf).exists() and Image.open(png).size == (3508, 2480)
    rec = AcademicRecord.objects.get(branch=jkt, aid=p.aid)
    assert rec.pct == 100 and "SPI21-2026008" in rec.cert and rec.sr_link.endswith(f"/{p.pk}/student-report/")
    s = StudentMaster.objects.get(branch=jkt, std="STD-000001")
    assert s.cert_level == "Development 2.1 · SPI21-2026008 · 2026-10-06" and s.level_in == "Development 2.2"
    assert AuditLog.objects.filter(branch=jkt, entity="FINAL_PROJECT").count() == 2
    with pytest.raises(ValidationError):
        services.setujui(jkt, manager, p.pk)                                         # tidak bisa disetujui dua kali


@pytest.mark.django_db
def test_level_without_template_still_gets_number_and_report(jkt, make_user):
    mgr = make_user("mgr2@spi.test", role="MANAGER", branch=jkt)
    p = services.setujui(jkt, mgr, _ajukan(jkt, mgr, std="STD-000002").pk, today=datetime.date(2026, 10, 6))
    assert p.cert_no == "SPI12-2026001" and not p.ada_sertifikat                      # level 1.2 belum punya template
    c = Client()
    c.force_login(mgr)
    assert "Template sertifikat level ini belum tersedia" in c.get(reverse("akademik:detail", args=[p.pk])).content.decode()
    assert c.get(reverse("akademik:rapor", args=[p.pk])).status_code == 200


@pytest.mark.django_db
def test_validation_and_rejection(jkt, make_user):
    mgr = make_user("mgr3@spi.test", role="MANAGER", branch=jkt)
    with pytest.raises(ValidationError):
        _ajukan(jkt, mgr, nilai_konsep=120)
    low = _ajukan(jkt, mgr, nilai_konsep=50, nilai_logika=50, nilai_kreativitas=60, nilai_presentasi=60)
    with pytest.raises(ValidationError):
        services.setujui(jkt, mgr, low.pk)                                           # di bawah batas lulus
    with pytest.raises(ValidationError):
        _ajukan(jkt, mgr)                                                             # level sama masih menunggu
    with pytest.raises(ValidationError):
        services.tolak(jkt, mgr, low.pk, alasan="")
    services.tolak(jkt, mgr, low.pk, alasan="Project belum selesai")
    assert FinalProject.objects.get(pk=low.pk).status == "DITOLAK"
    assert _ajukan(jkt, mgr).status == "DIAJUKAN"                                    # boleh ajukan ulang setelah ditolak


@pytest.mark.django_db
@pytest.mark.parametrize("role, submit, approve", [("ACADEMIC", 200, 403), ("MANAGER", 200, 302), ("BRANCH_ADMIN", 200, 302),
                                                   ("CSO", 403, 403), ("FINANCE", 403, 403)])
def test_roles(jkt, make_user, role, submit, approve):
    owner = make_user("owner@spi.test", role="MANAGER", branch=jkt)
    p = _ajukan(jkt, owner, std="STD-000002")
    c = Client()
    c.force_login(make_user(f"{role.lower()}@spi.test", role=role, branch=jkt))
    assert c.get(reverse("akademik:ajukan", args=["STD-000001"])).status_code == submit
    assert c.post(reverse("akademik:setujui", args=[p.pk])).status_code == approve
    assert c.get(reverse("akademik:list")).status_code == 200


@pytest.mark.django_db
def test_web_flow_and_branch_isolation(jkt, other_branch, make_user):
    mgr = make_user("mgr4@spi.test", role="MANAGER", branch=jkt)
    c = Client()
    c.force_login(mgr)
    form = {"judul": "Kalkulator Python", "tgl_selesai": "2026-10-03", **NILAI, "catatan": "Hebat!", "rekomendasi": "Development 2.2"}
    r = c.post(reverse("akademik:ajukan", args=["STD-000002"]), form)
    p = FinalProject.objects.get(branch=jkt, std="STD-000002")
    assert r.status_code == 302 and p.catatan == "Hebat!"
    assert "Tinjau" in c.get(reverse("akademik:list")).content.decode()
    assert "Final project selesai" in c.get(reverse("students:detail", args=["STD-000002"]), {"tab": "akademik"}).content.decode()
    other = make_user("lain@spi.test", role="MANAGER", branch=other_branch)
    c.force_login(other)
    assert c.get(reverse("akademik:detail", args=[p.pk])).status_code == 404
    assert c.get(reverse("akademik:ajukan", args=["STD-000002"])).status_code == 404


@pytest.mark.skipif(not (TEMPLATE_DIR / "sertifikat training 1.0.png").exists(), reason="template sertifikat tidak ada di mesin ini")
def test_every_template_renders(settings):
    settings.CERT_TEMPLATE_DIR = TEMPLATE_DIR
    for kode in certificates.TEMPLATES:
        img = certificates.render(kode, "Alberto Jayaharto", f"SPI{kode.replace('.', '')}-2026001", datetime.date(2026, 10, 6))
        assert img.size == (3508, 2480)
    with pytest.raises(ValueError):
        certificates.render("3.0", "X", "Y", datetime.date(2026, 10, 6))
