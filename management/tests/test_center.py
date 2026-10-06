import datetime

import pytest
from django.test import Client
from django.urls import reverse

from classes.models import Kehadiran, Sesi
from dashboards.tests.helpers import make_rows
from finance.models import BukuKas
from students.models import DBulan, StudentMaster

D = datetime.date


@pytest.mark.django_db
def test_management_center_uses_branch_data_and_marks_empty_billing_unavailable(
    branch, other_branch, make_user
):
    make_rows(
        StudentMaster,
        branch,
        {"std": "STD-000001", "v1": "M001", "nama": "Murid Jakarta", "prog_in": "Foundation"},
    )
    make_rows(
        StudentMaster,
        other_branch,
        {"std": "STD-000002", "v1": "M002", "nama": "Murid Cabang Lain"},
    )
    make_rows(
        DBulan,
        branch,
        {"key": "M001|202407", "v1": "M001", "bulan": D(2024, 7, 1), "status": "Aktif"},
    )
    manager = make_user("manager-center@spi.test", role="MANAGER", branch=branch)
    client = Client()
    client.force_login(manager)

    response = client.get(reverse("management:center"), {"periode": "2024-07"})
    html = response.content.decode()

    assert response.status_code == 200
    assert "Murid Jakarta" not in html
    assert "Murid Cabang Lain" not in html
    assert "Kesehatan SPI" in html and "Yang membutuhkan perhatian" in html
    assert "Belum ada tagihan untuk periode ini" in html          # tanpa buku kas: tidak ada angka buatan
    assert 'href="/manajemen/siklus-murid/' in html


@pytest.mark.django_db
def test_management_center_reports_recognized_cashbook_and_attendance_only_for_active_branch(
    branch, other_branch, make_user
):
    student = make_rows(
        StudentMaster,
        branch,
        {"std": "STD-000001", "v1": "M001", "nama": "Murid Jakarta", "harga": 250000},
    )[0]
    make_rows(
        DBulan,
        branch,
        {"key": "M001|202407", "v1": "M001", "bulan": D(2024, 7, 1), "status": "Aktif"},
    )
    make_rows(
        BukuKas,
        branch,
        {
            "lid": "KAS-1",
            "bulan": D(2024, 7, 1),
            "tgl": D(2024, 7, 5),
            "jenis": "SPP",
            "dihitung": "YA",
            "nominal": 250000,
            "per_sys": "2024-07",
            "ss1": student.std,
            "sb1": 250000,
        },
    )
    session, = make_rows(
        Sesi,
        branch,
        {"sid": "SES-1", "per": "2024-07", "status": "REALIZED"},
    )
    make_rows(
        Sesi,
        other_branch,
        {"sid": "SES-OTHER", "per": "2024-07", "status": "REALIZED"},
    )
    Kehadiran.objects.create(branch=branch, sid=session.sid, std=student.std, status="HADIR")
    Kehadiran.objects.create(branch=other_branch, sid="SES-OTHER", std="STD-OTHER", status="HADIR")
    manager = make_user("manager-center-cash@spi.test", role="MANAGER", branch=branch)
    client = Client()
    client.force_login(manager)

    response = client.get(reverse("management:center"), {"periode": "2024-07"})
    html = response.content.decode()

    assert response.status_code == 200
    assert "Rp 250.000" in html                                  # tagihan = harga SPP, diterima = buku kas periode itu
    assert "100,0%" in html                                      # collection 100% & sesi terlaksana dengan absensi (cabang ini saja)
    assert "BUKU_KAS" in html


@pytest.mark.django_db
def test_management_center_enforces_backend_permission(branch, make_user):
    user = make_user("staff-center@spi.test", role="CSO", branch=branch)
    client = Client()
    client.force_login(user)

    response = client.get(reverse("management:center"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_management_center_filters_student_metrics_and_reports_invalid_filters(branch, make_user):
    make_rows(
        StudentMaster,
        branch,
        {"std": "STD-000001", "v1": "M001", "prog_in": "Foundation", "guru_in": "Guru A"},
        {"std": "STD-000002", "v1": "M002", "prog_in": "Development", "guru_in": "Guru B"},
    )
    make_rows(
        DBulan,
        branch,
        {"key": "M001|202407", "v1": "M001", "bulan": D(2024, 7, 1), "status": "Aktif"},
        {"key": "M002|202407", "v1": "M002", "bulan": D(2024, 7, 1), "status": "Aktif"},
    )
    manager = make_user("manager-center-filter@spi.test", role="MANAGER", branch=branch)
    client = Client()
    client.force_login(manager)

    filtered_response = client.get(
        reverse("management:center"),
        {"periode": "2024-07", "program": "Foundation", "guru": "Guru A"},
    )
    invalid_response = client.get(
        reverse("management:center"),
        {"periode": "2024-07", "program": "Unknown program"},
    )

    assert filtered_response.status_code == 200
    assert filtered_response.context["snapshot"]["student_count"] == 1
    assert filtered_response.context["snapshot"]["current"]["aktif"] == 1
    assert invalid_response.status_code == 200
    assert "Program tidak dikenal." in invalid_response.context["filter_error"]
    assert invalid_response.context["snapshot"]["student_count"] == 2
