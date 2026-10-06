"""Business Health, Finance Control, Nota SPP, Operational Health, Data Health, Management Reports + ekspor.
Semua angka dari services/* (sumber yang sama dengan halaman operasional); cabang & izin dicek di server."""
import csv
import datetime
import io
from urllib.parse import quote

from django.contrib import messages
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core import audit
from core.ids import next_id, next_row_no
from core.permissions import has_perm, perms_for_caps, require_perm
from dashboards.calc.base import BranchData, KAS_START, chart, fold, label, parse_period, period_code, short_label
from finance.models import NotaLog
from students.models import StudentMaster

from .services import data_health, finance, health, lifecycle, operations

EKSPOR = ("csv", "xlsx")


def _data(request):
    return BranchData(request.branch, timezone.localdate())


def _perms(request):
    return perms_for_caps(getattr(request, "caps", frozenset()))


def _bulan(data, raw, default):
    d = parse_period(raw or "")
    return d if d in lifecycle.months(data) else default


def _ekspor(rows, header, nama, fmt):
    if fmt == "xlsx":
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = nama[:30]
        ws.append(header)
        for r in rows:
            ws.append(list(r))
        ws.freeze_panes = "A2"
        buf = io.BytesIO()
        wb.save(buf)
        resp = HttpResponse(buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(header)
        w.writerows(rows)
        resp = HttpResponse(("﻿" + buf.getvalue()).encode("utf-8"), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{nama}.{fmt}"'
    return resp


def _log_ekspor(request, apa):
    with transaction.atomic():
        audit.log(branch=request.branch, user=request.user, action="EXPORT", entity="LAPORAN", entity_id=apa, field="Ekspor manajemen", new=apa)


# ------------------------------------------------------------------ Business Health

@require_perm("management.view")
def business_health(request):
    data = _data(request)
    ms = lifecycle.months(data)
    bulan = _bulan(data, request.GET.get("periode"), ms[-1])
    r = health.ringkasan(data, bulan)
    ser = r["series"][:r["i"] + 1]
    last12 = ser[-12:]
    charts = [
        chart("bh-murid", "Murid aktif, baru, rejoin & Off baru · 12 bulan", [x["short"] for x in last12],
              [("Aktif", [x["aktif"] for x in last12]), ("Baru", [x["baru"] for x in last12]), ("Rejoin", [x["rejoin"] for x in last12]),
               ("Off baru", [x["off_baru"] or 0 for x in last12])], type="line"),
        chart("bh-retensi", "Retensi & churn bulanan (%)", [x["short"] for x in last12],
              [("Retensi", [x["retensi"] or 0 for x in last12]), ("Churn", [x["churn"] or 0 for x in last12])], type="line"),
    ]
    if "management.finance" in _perms(request):
        tr = finance.tren(data)
        charts.append(chart("bh-spp", "SPP: tagihan (estimasi) vs diterima per periode", [short_label(x["bulan"]) for x in tr],
                            [("Tagihan", [round(x["potensi"]) for x in tr]), ("Diterima", [round(x["diterima"]) for x in tr])], money=True))

    def banding(key, naik_baik=True):
        cur = r["cur"][key]
        rows = []
        for nama, j in (("Bulan lalu", r["i"] - 1), ("3 bulan lalu", r["i"] - 3), ("6 bulan lalu", r["i"] - 6), ("12 bulan lalu", r["i"] - 12)):
            prev = r["series"][j][key] if j >= 0 else None
            rows.append({"nama": nama, "nilai": prev, "tren": health._tren(cur, prev, naik_baik)})
        return rows

    metrik = [("Murid aktif", "aktif", True), ("Murid baru", "baru", True), ("Rejoin", "rejoin", True), ("Cuti", "cuti", False),
              ("Off baru", "off_baru", False), ("Retensi %", "retensi", True), ("Churn %", "churn", False)]
    return render(request, "management/health.html", {
        "r": r, "charts": charts, "periods": [{"code": period_code(m), "date": m} for m in reversed(ms)], "period_code": period_code(bulan),
        "banding": [{"nama": n, "nilai": r["cur"][k], "rows": banding(k, b)} for n, k, b in metrik],
        "ambang": health.AMBANG, "status": health.STATUS, "bobot": health.BOBOT_BISNIS, "definisi": lifecycle.DEFINISI,
    })


# ------------------------------------------------------------------ Finance Control

@require_perm("management.finance")
def finance_control(request):
    data = _data(request)
    pilihan = finance.periode_pilihan(data)
    bulan = parse_period(request.GET.get("periode", ""))
    bulan = bulan if bulan in pilihan else finance.periode_bawaan(data)
    program = request.GET.get("program", "")[:60]
    k = finance.kendali(data, bulan, program)
    fmt = request.GET.get("ekspor")
    risiko = finance.risiko_murid(data, bulan, k)
    if fmt in EKSPOR:
        _log_ekspor(request, f"Finance Control {k['label']}")
        rows = [(x.murid.std, x.murid.nama, finance.kode_dipakai(x.murid), x.murid.prog_in or x.murid.program, x.status, x.tagihan or "",
                 round(x.bayar), "" if x.sisa is None else round(x.sisa), x.sumber) for x in k["rows"]]
        return _ekspor(rows, ["Student ID", "Nama", "Kode kelas", "Program", "Status SPP", "Tagihan", "Diterima", "Sisa", "Dasar tagihan"],
                       f"finance-control-{period_code(bulan)}", fmt)
    tr = finance.tren(data, 12, program)
    kas_bulan = [x for x in data.kas_months if x >= KAS_START][-12:]
    from dashboards.calc.kas import bulanan
    per_bulan = {m: t for m, t, _l, _n in bulanan(data)}
    charts = [
        chart("fc-tren", "Tagihan vs diterima per periode tagihan", [short_label(x["bulan"]) for x in tr],
              [("Tagihan", [round(x["potensi"]) for x in tr]), ("Diterima", [round(x["diterima"]) for x in tr]),
               ("Sisa", [round(x["outstanding"]) for x in tr])], money=True,
              note="Sebelum Okt 2026 tagihan = harga SPP × murid aktif (estimasi). Agustus 2026 kosong: jurnal belum diputuskan."),
        chart("fc-kas", "Uang SPP masuk per bulan buku kas", [short_label(m) for m in kas_bulan], [("Masuk", [round(per_bulan.get(m, 0)) for m in kas_bulan])],
              money=True, note="Bulan uang diterima (sama dengan Laporan Murid & SPP), bukan periode tagihan."),
        chart("fc-coll", "Collection rate per periode (%)", [short_label(x["bulan"]) for x in tr], [("Collection", [x["collection"] or 0 for x in tr])], type="line"),
    ]
    branches = []
    if request.user.is_super_admin:
        from branches.models import Branch
        for b in Branch.objects.order_by("code"):
            d = BranchData(b, data.today)
            if not d.kas:
                branches.append({"b": b, "kosong": True})
                continue
            kb = finance.kendali(d, bulan)
            branches.append({"b": b, "k": kb})
    fmt_rp = lambda v: "Rp " + f"{round(v or 0):,}".replace(",", ".")
    sub = {"tagihan": f"{k['aktif']} murid aktif · {k['sumber']}", "diterima": f"semua penerimaan periode ini: {fmt_rp(k['diterima_semua'])}",
           "sisa": f"terlambat: {k['terlambat']} murid · {fmt_rp(k['terlambat_rp'])}",
           "coll_val": "—" if k["collection"] is None else f"{k['collection']}%",
           "coll": "lunas: " + ("—" if k["lunas_pct"] is None else f"{k['lunas_pct']}% murid aktif")}
    return render(request, "management/finance.html", {
        "catatan": finance.catatan_kas(data, bulan), "sub": sub, "belum_resmi": k["resmi"] and not k["potensi"], "k": k, "risiko": risiko, "charts": charts, "per_program": finance.per_program(k), "pilihan": pilihan, "program": program,
        "programs": data.programs, "branches": branches, "kas_tgl": finance.kas_terakhir_tgl(data), "status_list": list(k["hitung"].items()),
    })


# ------------------------------------------------------------------ Nota SPP

@require_perm("management.finance")
def nota(request):
    data = _data(request)
    q = request.GET.get("q", "")[:60].strip()
    pilihan = finance.periode_pilihan(data)
    bulan = parse_period(request.GET.get("periode", ""))
    bulan = bulan if bulan in pilihan else finance.periode_bawaan(data)
    hasil = []
    if len(q) >= 2:
        qf = fold(q)
        for s in data.students:
            if s.std and (qf in fold(s.nama) or qf in fold(s.std)):
                hasil.append(finance.status_bayar(data, s, bulan))
                if len(hasil) >= 25:
                    break
    log = list(NotaLog.objects.for_branch(request.branch).order_by("-tgl", "-row_no")[:15])
    return render(request, "management/nota_index.html", {"q": q, "hasil": hasil, "pilihan": pilihan, "bulan": bulan, "log": log})


def _murid(request, std):
    s = StudentMaster.objects.for_branch(request.branch).filter(std=std).first()
    if s is None:
        raise Http404("Murid tidak ditemukan di cabang ini")
    return s


def _nota_ctx(request, data, s, bulan, log=None):
    st = finance.status_bayar(data, s, bulan)
    par = finance.orang_tua(data, s)
    wa = ""
    if par and par.wa and has_perm(request, "student.contacts"):
        nomor = data_health._digits(par.wa)
        teks = (f"Yth. {finance.kepada(data, s)}, berikut Nota SPP {s.nama} periode {label(bulan)}: "
                f"tagihan Rp {int(st.tagihan or 0):,}, tercatat Rp {int(st.bayar):,}, sisa Rp {int(st.sisa or 0):,} ({st.status}). "
                f"Terima kasih - {data.setting('nota_kop', request.branch.name)}").replace(",", ".")
        wa = f"https://wa.me/{nomor}?text={quote(teks)}"
    if log:
        tg, by = log.tagihan, log.bayar or 0
        doc = {"tagihan": tg, "bayar": by, "status": log.status, "sisa": None if tg is None else max(0, tg - by), "kepada": log.kepada}
    else:
        doc = {"tagihan": st.tagihan, "bayar": st.bayar, "status": st.status, "sisa": st.sisa, "kepada": finance.kepada(data, s)}
    doc["lebih"] = doc["tagihan"] is not None and doc["bayar"] > doc["tagihan"]
    doc["nada"] = finance.NADA.get(doc["status"], "st-netral")
    return {"doc": doc, "judul": f"Nota SPP · periode {label(bulan)}", "s": s, "st": st, "bulan": bulan, "kepada": finance.kepada(data, s), "kop": data.setting("nota_kop", request.branch.name),
            "instruksi": data.setting("nota_instruksi", ""), "kas_tgl": finance.kas_terakhir_tgl(data), "log": log,
            "riwayat": finance.riwayat_nota(data, s), "wa": wa, "kode": finance.kode_dipakai(s),
            "level": s.level_in or s.level or s.prog_in or s.program or "-",
            "perkiraan_no": None if log else _perkiraan(data, request.branch), "today": data.today}


def _perkiraan(data, branch):
    prefix = f"{finance.awalan_nota(data)}{data.today.year}/"
    top = 0
    for v in NotaLog.objects.filter(branch=branch, no__startswith=prefix).values_list("no", flat=True):
        rest = v[len(prefix):]
        if rest.isdigit():
            top = max(top, int(rest))
    return f"{prefix}{top + 1:04d}"


@require_perm("management.finance")
def nota_preview(request, std, per):
    data = _data(request)
    bulan = parse_period(per)
    if bulan is None:
        raise Http404("Periode tidak valid")
    s = _murid(request, std)
    return render(request, "management/nota.html", _nota_ctx(request, data, s, bulan))


@require_POST
@require_perm("nota.issue")
def nota_issue(request, std, per):
    data = _data(request)
    bulan = parse_period(per)
    s = _murid(request, std)
    if bulan is None:
        raise Http404("Periode tidak valid")
    st = finance.status_bayar(data, s, bulan)
    if not st.bisa_nota:
        messages.error(request, st.pesan or f"Nota tidak bisa dibuat: {st.status}.")
        return redirect("management:nota_preview", std=std, per=per)
    with transaction.atomic():
        no = next_id(NotaLog, "no", f"{finance.awalan_nota(data)}{data.today.year}/", 4, request.branch)
        row = NotaLog.objects.create(
            branch=request.branch, row_no=next_row_no(NotaLog, request.branch), no=no, tgl=timezone.now(), std=s.std, nama=s.nama,
            periode=label(bulan), kepada=finance.kepada(data, s), tagihan=st.tagihan, bayar=st.bayar, status=st.status,
            user=request.user.display_name, catatan=f"Dasar tagihan: {st.sumber}; buku kas s/d {finance.kas_terakhir_tgl(data) or '-'}")
        audit.log(branch=request.branch, user=request.user, action="CREATE", entity="NOTA_LOG", entity_id=no, field="Nota SPP",
                  new=f"{s.std} {label(bulan)} {st.status} tagihan {int(st.tagihan or 0)} bayar {int(st.bayar)}")
    messages.success(request, f"Nota {no} diterbitkan untuk {s.nama} ({label(bulan)}).")
    return redirect("management:nota_view", pk=row.pk)


@require_perm("management.finance")
def nota_view(request, pk):
    log = NotaLog.objects.for_branch(request.branch).filter(pk=pk).first()
    if log is None:
        raise Http404("Nota tidak ditemukan")
    data = _data(request)
    s = _murid(request, log.std)
    bulan = next((m for m in lifecycle.months(data) if label(m) == log.periode), None)
    if bulan is None:
        raise Http404("Periode nota tidak dikenal")
    return render(request, "management/nota.html", _nota_ctx(request, data, s, bulan, log=log))


# ------------------------------------------------------------------ Operational Health

@require_perm("management.view")
def operational(request):
    data = _data(request)
    ms = lifecycle.months(data)
    bulan = _bulan(data, request.GET.get("periode"), ms[-1])
    op = operations.operasional(data, bulan)
    if request.GET.get("ekspor") in EKSPOR:
        _log_ekspor(request, f"Beban guru {label(bulan)}")
        rows = [(g["t"].tid, g["t"].name, g["t"].status, g["aktif"], g["kelas"], g["slot"], g["sesi"], g["rasio"] or "", g["catatan"]) for g in op["guru"]]
        return _ekspor(rows, ["Teacher ID", "Guru", "Status", "Murid aktif", "Kelas", "Slot jadwal", "Sesi terlaksana bulan ini", "Rasio beban", "Catatan"],
                       f"operasional-guru-{period_code(bulan)}", request.GET["ekspor"])
    kh = op["kehadiran"]
    sub = {"sesi": f"{op['sesi']['realisasi']} terlaksana · hari ini {op['sesi']['hari_ini']}",
           "hadir_val": "—" if kh["pct"] is None else f"{kh['pct']}%", "hadir": f"{kh['hadir']} hadir dari {kh['total']} catatan",
           "fu": f"{op['followup']['terbuka']} terbuka · hari ini {op['followup']['hari_ini']}"}
    return render(request, "management/operations.html", {"op": op, "periods": [{"code": period_code(m), "date": m} for m in reversed(ms)],
                                                           "period_code": period_code(bulan), "sub": sub, "followup_url": reverse("students:followups")})


# ------------------------------------------------------------------ Data Health

@require_perm("management.view")
def data_health_view(request):
    data = _data(request)
    cek = data_health.cek_semua(data)
    if request.GET.get("ekspor") in EKSPOR:
        _log_ekspor(request, "Data Health")
        rows = [(c.kategori, c.judul, c.tingkat, it["label"], it["detail"], request.build_absolute_uri(it["url"]) if it["url"] else "", c.aksi, c.sumber)
                for c in cek for it in c.terkena]
        return _ekspor(rows, ["Kategori", "Cek", "Tingkat", "Catatan", "Detail", "Tautan", "Aksi", "Sumber"], "data-health", request.GET["ekspor"])
    kategori = {}
    for c in cek:
        kategori.setdefault(c.kategori, []).append(c)
    skor = data_health.skor(cek)
    st, nada = health.status_skor(skor)
    return render(request, "management/data.html", {
        "kategori": [{"nama": k, "cek": v, "skor": data_health.skor(v)} for k, v in kategori.items()], "skor": skor, "status": st, "nada": nada,
        "total_terkena": sum(c.n for c in cek), "bobot": data_health.BOBOT, "tampil": data_health.TAMPIL,
        "prioritas": sorted([c for c in cek if c.n], key=lambda c: (-data_health.BOBOT[c.tingkat], -c.n))[:6],
    })


# ------------------------------------------------------------------ Management Reports

@require_perm("management.view")
def reports(request):
    data = _data(request)
    ms = lifecycle.months(data)
    return render(request, "management/reports.html", {"periods": [{"code": period_code(m), "date": m} for m in reversed(ms)],
                                                       "finance": "management.finance" in _perms(request)})


@require_perm("management.view")
def report_monthly(request):
    data = _data(request)
    ms = lifecycle.months(data)
    bulan = _bulan(data, request.GET.get("periode"), ms[-1])
    perms = _perms(request)
    r = health.ringkasan(data, bulan)
    return render(request, "management/report_monthly.html", {
        "r": r, "keputusan": health.keputusan(data, r, perms), "finance": "management.finance" in perms, "dibuat": timezone.localtime(),
        "impor": data.last_import.date if data.last_import else None,
        "wawasan": {k: len(v) for k, v in lifecycle.wawasan(data, r["rows"]).items()}, "kategori_nada": health.KATEGORI_NADA,
    })


@require_perm("management.view")
def export_lifecycle(request):
    data = _data(request)
    fmt = request.GET.get("format", "xlsx")
    if fmt not in EKSPOR:
        fmt = "xlsx"
    ms = lifecycle.months(data)
    rows = [(i + 1, b.nama, b.std, b.v1, b.kode, b.program, b.tipe, *b.huruf, b.bulan_aktif, lifecycle.ARTI.get(b.kode_terakhir, ""))
            for i, b in enumerate(lifecycle.matrix(data))]
    _log_ekspor(request, "Matriks Student Lifecycle")
    return _ekspor(rows, ["No", "Nama", "Student ID", "ID v1", "Kode kelas", "Program", "Tipe", *[short_label(m) for m in ms],
                          "Bulan aktif (Jan 2024-Sep 2026)", "Status terakhir"], "student-lifecycle", fmt)


@require_perm("management.view")
def export_lifecycle_kpi(request):
    data = _data(request)
    fmt = request.GET.get("format", "xlsx") if request.GET.get("format") in EKSPOR else "xlsx"
    rows = [(x["label"], x["aktif"], x["baru"], x["rejoin"], x["cuti"], x["off"], x["off_baru"] if x["off_baru"] is not None else "",
             x["basis"] if x["basis"] is not None else "", x["retensi"] if x["retensi"] is not None else "", x["churn"] if x["churn"] is not None else "",
             x["hilang"] if x["hilang"] is not None else "", x["reaktivasi"] if x["reaktivasi"] is not None else "",
             x["konversi"] if x["konversi"] is not None else "") for x in lifecycle.series(data)]
    _log_ekspor(request, "KPI lifecycle bulanan")
    return _ekspor(rows, ["Bulan", "Aktif", "Baru", "Rejoin", "Cuti", "Off", "Off baru", "Basis", "Retensi %", "Churn %", "Hilang dari catatan",
                          "Reaktivasi %", "Konversi baru→aktif %"], "lifecycle-kpi-bulanan", fmt)
