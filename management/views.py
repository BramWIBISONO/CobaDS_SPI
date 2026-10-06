from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import timezone

from core.permissions import require_perm
from dashboards.calc.base import BranchData, parse_period, period_code

from .services.lifecycle import (
    ARTI,
    BELUM_MASUK,
    DEFINISI,
    filtered,
    matrix,
    months,
    wawasan,
)
from core.permissions import perms_for_caps

from .services import health
from .services.overview import build_overview


ROWS_PER_PAGE = 100
CELL_CSS = {"A": "lc-A", "B": "lc-B", "R": "lc-R", "C": "lc-C", "O": "lc-O", "?": "lc-q"}
STATUS_FILTERS = (
    ("", "Semua status"),
    ("aktif", "Aktif (A/B/R)"),
    ("B", "Baru"),
    ("R", "Rejoin"),
    ("C", "Cuti"),
    ("O", "OFF"),
    ("?", "Status kosong (?)"),
    (BELUM_MASUK, "Belum masuk SPI (–)"),
    ("·", "Tidak tercatat setelah OFF (·)"),
)
SORTS = {"nama": "Nama", "id": "Student ID", "aktif": "Bulan aktif", "status": "Status terakhir"}
INSIGHT_GROUPS = (
    ("mendekati_off", "Cuti berulang"),
    ("baru_off", "Baru menjadi OFF"),
    ("kembali", "Kembali dari OFF"),
    ("lama_tidak_aktif", "Lama tidak aktif"),
    ("status_kosong", "Status kosong terbaru"),
    ("tidak_biasa", "Perubahan status tidak biasa"),
)


def _display_status(raw):
    return {
        "ACTIVE": "Aktif",
        "ON LEAVE": "Cuti",
        "OFF": "OFF",
        "PENDING": "Belum ditentukan",
    }.get(str(raw or "").strip().upper(), raw or "Tidak tercatat")


@require_perm("management.view")
def center(request):
    data = BranchData(request.branch, timezone.localdate())
    all_months = months(data)
    month_indexes = {period_code(month): i for i, month in enumerate(all_months)}
    period_code_selected = request.GET.get("periode", period_code(all_months[-1]))
    filter_errors = []
    if period_code_selected not in month_indexes:
        period_code_selected = period_code(all_months[-1])
        filter_errors.append("Periode tidak valid atau di luar rentang data.")
    selected_index = month_indexes[period_code_selected]
    selected_month = all_months[selected_index]

    query = {
        "program": request.GET.get("program", ""),
        "guru": request.GET.get("guru", ""),
    }
    rows = matrix(data)
    programs = sorted({row.program for row in rows if row.program}, key=str.casefold)
    teachers = sorted({row.guru for row in rows if row.guru}, key=str.casefold)
    if query["program"] and query["program"] not in programs:
        query["program"] = ""
        filter_errors.append("Program tidak dikenal.")
    if query["guru"] and query["guru"] not in teachers:
        query["guru"] = ""
        filter_errors.append("Guru tidak dikenal.")
    scoped_rows = filtered(
        rows,
        program=query["program"],
        guru=query["guru"],
        kolom=selected_index,
    )
    snapshot = build_overview(data, selected_month, scoped_rows, selected_index)
    all_periods = [
        {"date": month, "code": period_code(month)}
        for month in all_months
    ]

    r = health.ringkasan(data, selected_month, query["program"], query["guru"])
    cabang = []
    if request.user.is_super_admin:
        from branches.models import Branch
        for b in Branch.objects.order_by("code"):
            d = data if b.pk == request.branch.pk else BranchData(b, data.today)
            cabang.append({"b": b, "kosong": True} if not d.students else {"b": b, "r": r if d is data else health.ringkasan(d, selected_month)})
    return render(request, "management/center.html", {
        "r": r, "keputusan": health.keputusan(data, r, perms_for_caps(getattr(request, "caps", frozenset()))), "cabang": cabang,
        "snapshot": snapshot,
        "periods": all_periods,
        "period_code": period_code_selected,
        "programs": programs,
        "teachers": teachers,
        "query": query,
        "filter_error": " ".join(filter_errors),
        "last_import": data.last_import.date if data.last_import and data.last_import.date else None,
    })


@require_perm("management.view")
def lifecycle(request):
    data = BranchData(request.branch, timezone.localdate())
    all_months = months(data)
    month_indexes = {period_code(month): i for i, month in enumerate(all_months)}
    first_code, last_code = period_code(all_months[0]), period_code(all_months[-1])
    from_code = request.GET.get("dari", first_code)
    to_code = request.GET.get("sampai", last_code)
    from_month, to_month = parse_period(from_code), parse_period(to_code)
    filter_error = ""

    if from_month is None or period_code(from_month) not in month_indexes:
        filter_error = "Periode awal tidak valid atau di luar rentang data."
        from_code, from_month = first_code, all_months[0]
    if to_month is None or period_code(to_month) not in month_indexes:
        filter_error = "Periode akhir tidak valid atau di luar rentang data."
        to_code, to_month = last_code, all_months[-1]
    if from_month > to_month:
        filter_error = "Periode awal harus sebelum atau sama dengan periode akhir."
        from_code, to_code = first_code, last_code
        from_month, to_month = all_months[0], all_months[-1]

    rows = matrix(data)
    query = {
        "q": request.GET.get("q", "")[:100].strip(),
        "program": request.GET.get("program", ""),
        "kode": request.GET.get("kelas", ""),
        "guru": request.GET.get("guru", ""),
        "mode": request.GET.get("mode", ""),
        "status": request.GET.get("status", ""),
    }
    valid_statuses = {value for value, _label in STATUS_FILTERS}
    if query["status"] not in valid_statuses:
        filter_error = "Status filter tidak dikenal."
        query["status"] = ""

    start_index, end_index = month_indexes[period_code(from_month)], month_indexes[period_code(to_month)]
    filtered_rows = filtered(
        rows,
        q=query["q"],
        program=query["program"],
        kode=query["kode"],
        guru=query["guru"],
        mode=query["mode"],
        status=query["status"],
        kolom=end_index,
    )
    attention_rows = filtered(
        rows,
        q=query["q"],
        program=query["program"],
        kode=query["kode"],
        guru=query["guru"],
        mode=query["mode"],
    )
    raw_insights = wawasan(data, attention_rows)
    attention_groups = [
        {"title": title, "items": raw_insights[key]}
        for key, title in INSIGHT_GROUPS
        if raw_insights[key]
    ]

    sort = request.GET.get("urut", "nama")
    if sort not in SORTS:
        filter_error = "Pilihan pengurutan tidak dikenal."
        sort = "nama"
    reverse = request.GET.get("arah", "naik") == "turun"
    sort_key = {
        "nama": lambda row: row.nama.casefold(),
        "id": lambda row: row.std.casefold(),
        "aktif": lambda row: row.bulan_aktif,
        "status": lambda row: row.kode_terakhir,
    }[sort]
    filtered_rows.sort(key=sort_key, reverse=reverse)

    selected = next((row for row in rows if row.std == request.GET.get("murid")), None)
    selected_month = parse_period(request.GET.get("bulan", ""))
    selected_cell = None
    if selected is not None and selected_month is not None:
        selected_month_index = month_indexes.get(period_code(selected_month))
        if selected_month_index is not None:
            selected_cell = {
                "month": selected_month,
                "code": selected.huruf[selected_month_index],
                "meaning": ARTI.get(selected.huruf[selected_month_index], "Status tidak dikenal"),
                "raw": _display_status(selected.raw[selected_month_index]),
            }

    query_params = request.GET.copy()
    for key in ("murid", "bulan", "hal"):
        query_params.pop(key, None)
    base_qs = query_params.urlencode()
    base_qs = f"{base_qs}&" if base_qs else ""
    page = Paginator(filtered_rows, ROWS_PER_PAGE).get_page(request.GET.get("hal"))
    shown_months = all_months[start_index:end_index + 1]
    month_codes = [(month, period_code(month)) for month in shown_months]
    display_rows = []
    for row in page.object_list:
        cells = []
        for (month, code_month), month_index in zip(month_codes, range(start_index, end_index + 1)):
            code = row.huruf[month_index]
            raw = _display_status(row.raw[month_index]) if row.raw[month_index] else ""
            cells.append({"month": month, "kode_bulan": code_month, "code": code, "css": CELL_CSS.get(code, "lc-n"),
                          "title": f"{month:%m/%Y} · {ARTI.get(code, 'Status tidak dikenal')}{' · ' + raw if raw else ''}"})
        display_rows.append({
            "row": row,
            "cells": cells,
            "recent_cells": cells[-6:],
            "last_status": _display_status(row.terakhir),
        })

    context = {
        "rows": display_rows,
        "page": page,
        "base_qs": base_qs,
        "offset": page.start_index() - 1 if page.paginator.count else 0,
        "months": shown_months,
        "definitions": DEFINISI,
        "status_filters": STATUS_FILTERS,
        "programs": data.programs,
        "classes": sorted({row.kode for row in rows if row.kode}, key=str.casefold),
        "teachers": sorted({row.guru for row in rows if row.guru}, key=str.casefold),
        "modes": sorted({row.mode for row in rows if row.mode}, key=str.casefold),
        "query": query,
        "from_code": from_code,
        "to_code": to_code,
        "first_code": first_code,
        "last_code": last_code,
        "filter_error": filter_error,
        "sort": sort,
        "reverse": reverse,
        "sorts": SORTS,
        "selected": selected,
        "selected_cell": selected_cell,
        "matched_count": len(filtered_rows),
        "active_count": sum(row.huruf[end_index] in {"A", "B", "R"} for row in filtered_rows),
        "current_period": all_months[end_index],
        "attention_groups": attention_groups,
        "attention_count": sum(len(group["items"]) for group in attention_groups),
    }
    return render(request, "management/lifecycle.html", context)
