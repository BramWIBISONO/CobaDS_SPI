import datetime

import pytest
from django.test import Client
from django.urls import reverse

from dashboards.calc.base import BranchData
from management.services.lifecycle import (
    BELUM_MASUK,
    KOSONG,
    SETELAH_OFF,
    filtered,
    kpi_bulan,
    matrix,
    wawasan,
)
from students.models import DBulan, StatusEvent, StudentMaster
from dashboards.tests.helpers import make_rows

D = datetime.date


@pytest.mark.django_db
def test_matrix_maps_historical_status_and_missing_rows(branch):
    student, no_history = make_rows(
        StudentMaster,
        branch,
        {"std": "STD-000001", "v1": "M001", "nama": "Satu"},
        {"std": "STD-000002", "v1": "M002", "nama": "Dua"},
    )
    make_rows(
        DBulan,
        branch,
        {"key": "M001|202401", "v1": "M001", "bulan": D(2024, 1, 1), "status": "Aktif"},
        {"key": "M001|202402", "v1": "M001", "bulan": D(2024, 2, 1), "status": ""},
        {"key": "M001|202403", "v1": "M001", "bulan": D(2024, 3, 1), "status": "Baru"},
        {"key": "M001|202404", "v1": "M001", "bulan": D(2024, 4, 1), "status": "Rejoin"},
        {"key": "M001|202405", "v1": "M001", "bulan": D(2024, 5, 1), "status": "Cuti"},
        {"key": "M001|202406", "v1": "M001", "bulan": D(2024, 6, 1), "status": "Off"},
        {"key": "M001|202409", "v1": "M001", "bulan": D(2024, 9, 1), "status": "Lulus"},
    )

    rows = matrix(BranchData(branch, D(2026, 9, 30)))
    one, two = rows
    assert one.huruf[:8] == ["A", KOSONG, "B", "R", "C", "O", SETELAH_OFF, SETELAH_OFF]
    assert one.huruf[8] == BELUM_MASUK
    assert two.huruf[:3] == [BELUM_MASUK] * 3
    assert one.raw[8] == "Lulus"
    assert one.terakhir == ""
    assert one.kode_terakhir == BELUM_MASUK


@pytest.mark.django_db
def test_monthly_active_total_matches_excel_range_and_last_status_is_raw(branch):
    student = make_rows(
        StudentMaster,
        branch,
        {"std": "STD-000001", "v1": "M001", "st_base": "ACTIVE"},
    )[0]
    make_rows(
        DBulan,
        branch,
        {"key": "M001|202401", "v1": "M001", "bulan": D(2024, 1, 1), "status": "Aktif"},
        {"key": "M001|202609", "v1": "M001", "bulan": D(2026, 9, 1), "status": "Aktif"},
    )

    row = matrix(BranchData(branch, D(2026, 10, 6)))[0]
    assert row.bulan_aktif == 2
    assert row.bulan_aktif_sampai_sekarang == 3
    assert row.terakhir == "ACTIVE"
    assert row.status_terakhir_historis == "Aktif"
    assert row.kode_terakhir == "A"


@pytest.mark.django_db
def test_current_month_ignores_status_events_after_today(branch):
    student = make_rows(
        StudentMaster,
        branch,
        {"std": "STD-000001", "v1": "M001", "st_base": "ACTIVE"},
    )[0]
    make_rows(
        DBulan,
        branch,
        {"key": "M001|202609", "v1": "M001", "bulan": D(2026, 9, 1), "status": "Aktif"},
    )
    make_rows(
        StatusEvent,
        branch,
        {"eid": "EVT-000001", "std": student.std, "tgl": D(2026, 10, 31), "status": "OFF"},
    )

    row = matrix(BranchData(branch, D(2026, 10, 6)))[0]
    assert row.raw[-1] == "ACTIVE"
    assert row.kode_terakhir == "A"


@pytest.mark.django_db
def test_off_return_missing_status_and_long_inactive_insights(branch):
    returned, newly_off, inactive, missing = make_rows(
        StudentMaster,
        branch,
        {"std": "STD-000001", "v1": "M001", "st_base": "OFF"},
        {"std": "STD-000002", "v1": "M002", "st_base": "ACTIVE"},
        {"std": "STD-000003", "v1": "M003", "st_base": "OFF"},
        {"std": "STD-000004", "v1": "M004", "st_base": "ACTIVE"},
    )
    make_rows(
        DBulan,
        branch,
        {"key": "M001|202609", "v1": "M001", "bulan": D(2026, 9, 1), "status": "Off"},
        {"key": "M002|202609", "v1": "M002", "bulan": D(2026, 9, 1), "status": "Aktif"},
        {"key": "M003|202401", "v1": "M003", "bulan": D(2024, 1, 1), "status": "Aktif"},
        {"key": "M003|202402", "v1": "M003", "bulan": D(2024, 2, 1), "status": "Off"},
        {"key": "M004|202601", "v1": "M004", "bulan": D(2026, 1, 1), "status": "Aktif"},
    )
    make_rows(
        StatusEvent,
        branch,
        {"eid": "EVT-000001", "std": returned.std, "tgl": D(2026, 10, 3), "status": "ACTIVE"},
        {"eid": "EVT-000002", "std": newly_off.std, "tgl": D(2026, 10, 3), "status": "OFF"},
    )
    data = BranchData(branch, D(2026, 10, 6))
    rows = matrix(data)
    by_id = {row.std: row for row in rows}
    assert by_id[returned.std].kode_terakhir == "R"
    assert by_id[newly_off.std].kode_terakhir == "O"

    insights = wawasan(data, rows)
    assert [row.std for row, _reason in insights["kembali"]] == [returned.std]
    assert [row.std for row, _reason in insights["baru_off"]] == [newly_off.std]
    assert [row.std for row, _reason in insights["lama_tidak_aktif"]] == [inactive.std]
    assert [row.std for row, _reason in insights["status_kosong"]] == [missing.std]


@pytest.mark.django_db
def test_matrix_and_filters_are_branch_scoped(branch, other_branch):
    make_rows(StudentMaster, branch, {"std": "STD-000001", "v1": "M001", "nama": "Alya", "kode_in": "F01"})
    make_rows(StudentMaster, other_branch, {"std": "STD-000002", "v1": "M002", "nama": "Bram", "kode_in": "F01"})

    rows = matrix(BranchData(branch, D(2026, 9, 30)))
    assert [row.std for row in rows] == ["STD-000001"]
    assert [row.std for row in filtered(rows, q="alya", kode="F01")] == ["STD-000001"]
    assert filtered(rows, q="Bram") == []


def test_empty_denominators_are_unavailable_not_zero_percent():
    from types import SimpleNamespace

    row = SimpleNamespace(huruf=["A", "A"])
    month = kpi_bulan([row], 1)
    assert month["basis"] == 1
    assert month["retensi"] == 100.0
    assert month["reaktivasi"] is None


@pytest.mark.django_db
def test_lifecycle_page_uses_branch_data_filters_and_student_links(branch, other_branch, make_user):
    make_rows(
        StudentMaster,
        branch,
        {
            "std": "STD-000001",
            "v1": "M001",
            "nama": "Murid Jakarta",
            "kode_in": "F01",
            "prog_in": "Foundation",
            "guru_in": "Guru A",
            "mode": "Online",
        },
    )
    make_rows(
        StudentMaster,
        other_branch,
        {"std": "STD-000002", "v1": "M002", "nama": "Murid Cabang Lain"},
    )
    make_rows(
        DBulan,
        branch,
        {
            "key": "M001|202401",
            "v1": "M001",
            "bulan": D(2024, 1, 1),
            "status": "Aktif",
            "grade": "Foundation 1.0",
        },
    )
    manager = make_user("manager@spi.test", role="MANAGER", branch=branch)
    client = Client()
    client.force_login(manager)

    response = client.get(
        reverse("management:lifecycle"),
        {
            "q": "STD-000001",
            "dari": "2024-01",
            "sampai": "2024-01",
            "program": "Foundation",
            "kelas": "F01",
            "guru": "Guru A",
            "mode": "Online",
            "status": "aktif",
            "urut": "status",
            "arah": "turun",
        },
    )

    assert response.status_code == 200
    assert "Murid Jakarta" in response.content.decode()
    assert "Murid Cabang Lain" not in response.content.decode()
    assert reverse("students:detail", args=["STD-000001"]) in response.content.decode()


@pytest.mark.django_db
def test_lifecycle_page_requires_management_permission(branch, make_user):
    user = make_user("cso@spi.test", role="CSO", branch=branch)
    client = Client()
    client.force_login(user)

    response = client.get(reverse("management:lifecycle"))

    assert response.status_code == 403
