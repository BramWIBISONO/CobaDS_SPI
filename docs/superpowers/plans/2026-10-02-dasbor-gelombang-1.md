# Dasbor Gelombang 1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sistem desain gaya B, halaman Beranda dan Laporan Murid & SPP yang angkanya sama persis dengan Excel v4, serta akun demo per peran untuk dicoba di laptop.

**Architecture:** App baru `dashboards` berisi paket `calc` (satu modul per lembar hitung Excel: status, laporan/C_DASH, kas/C_KAS, kelas, off, operasional, beranda) yang membaca data cabang sekali per permintaan lewat `BranchData`. Halaman memakai komponen template bersama (kartu KPI berwarna, kartu grafik Chart.js) dan HTMX untuk filter. Kesamaan dengan Excel dibuktikan oleh angka emas yang dihitung Excel sendiri (alat COM pada salinan workbook) dan diuji tanpa toleransi.

**Tech Stack:** Django 5.2, PostgreSQL (pgserver), pytest, Tailwind CSS 4, HTMX, Alpine.js, Chart.js 4, Plus Jakarta Sans (@fontsource), Tabler Icons webfont, pywin32 (alat angka emas, Python sistem).

**Spec:** `docs/superpowers/specs/2026-10-02-dasbor-gelombang-1-design.md` (dasar: `docs/superpowers/specs/2026-09-30-spi-web-design.md`)

## Global Constraints

- Angka web = Excel untuk data, bulan/filter, dan tanggal "hari ini" yang sama; tidak ada definisi baru. Perbandingan teks Excel tidak membedakan huruf besar/kecil.
- Item yang logikanya belum ada tampil "menyusul": kartu Perlu tindakan; Tagihan belum dibayar dan tagihan/terbayar/sisa; Cuti ≥ 2 bulan & sesi belum dikonfirmasi; kartu "Nama menunggu".
- Workbook `..\APP` hanya dibaca; alat angka emas memakai salinan di folder sementara dan menutup Excel miliknya sendiri.
- Angka emas hanya berisi Student ID / ID v1 / Off Record ID / ID Baris dan angka/status — tanpa nama murid atau kontak.
- Hari ini untuk uji = 30 Sep 2026; halaman memakai `timezone.localdate()`.
- Gaya B: warna topik murid biru, spp hijau, off kuning, kelas ungu, kritis merah, akad toska; aset (font, ikon, Chart.js) disajikan lokal dari `static/vendor`.
- Akun demo hanya aktif bila `DEBUG=True` dan `DEMO_ACCOUNTS=True`; kata sandi demo hanya di `.env`.
- Perintah dari folder `app web` (Git Bash); Python lewat `.venv/Scripts/python`; alat angka emas lewat `python` sistem (pywin32).

## Review Focus

1. Cabang tanpa data (Alam Sutera / cabang baru) → Beranda & Laporan tampil tanpa error: nol, daftar kosong, "—" (Task 8, Task 9).
2. Parameter URL tidak sah (`bulan=xx`, `guru=<script>`, `daftar=apa`) → kembali ke bawaan, tidak 500, teks di-escape (Task 9).
3. Bulan sebelum buku kas (Jan–Jun 2024) → kartu SPP "—", bukan 0 (Task 5).
4. Agustus 2026 dengan jurnal belum diputuskan → "perlu keputusan" (Task 5).
5. Teacher / pengguna cabang lain → tidak bisa membuka Laporan atau hasil cari murid cabang lain (Task 8, Task 9).

## File Structure

```
app web/
  tools/export_golden.py                 alat angka emas (Python sistem + pywin32)
  dashboards/                            app baru
    apps.py  urls.py  views.py  pages.py (rakit konteks halaman dari calc)
    calc/  base.py (BranchData, helper)  status.py  laporan.py  kas.py  kelas.py  off.py  operasional.py  beranda.py
    templatetags/spi.py                  format rupiah / angka / tone status
    templates/dashboards/  beranda.html  _cari_hasil.html  laporan.html  _laporan_body.html
    tests/  golden/jkt_golden.json  test_golden_fixture.py  test_golden.py (slow)  test_status.py  test_laporan.py  test_kas.py
            test_kelas_off.py  test_beranda_view.py  test_laporan_view.py
  templates/components/  kpi_card.html  chart_card.html  status_badge.html
  static/js/dashboards.js                grafik Chart.js
  accounts/  demo.py  checks.py  management/commands/seed_demo_accounts.py  tests/test_demo.py
  docs/AKUN_DEMO.md
```

---

### Task 1: Perbaikan impor — kolom Dihitung buku kas disimpan

**Files:**
- Modify: `tools/export_schema.py`, `importer/tests/test_schema_models.py`
- Regenerate: `importer/schema/excel_tables.json`, `finance/models_excel.py`; Create: `finance/migrations/0002_*.py`

**Interfaces:**
- Produces: `finance.BukuKas.dihitung` (TextField, nilai tersimpan "YA"/"TIDAK" dari workbook).

- [ ] **Step 1: Uji yang gagal**

Tambahkan ke akhir `importer/tests/test_schema_models.py`:
```python


def test_cash_book_counted_flag_is_stored():
    # Dihitung = nilai tetap di semua baris kecuali Agustus 2026 (rumus pilihan jurnal) -> harus ikut diimpor
    assert table("BUKU_KAS").field_by_header["Dihitung"].stored is True
```

Run: `.venv/Scripts/python -m pytest importer/tests/test_schema_models.py`
Expected: FAIL pada `test_cash_book_counted_flag_is_stored`.

- [ ] **Step 2: Ekspor skema menyimpan kolom itu**

Modify `tools/export_schema.py` — di bawah baris `STOP_AT_BLANK = ...` tambahkan:
```python
STORED_FORMULA = {("BUKU_KAS", "dihitung")}       # rumus hanya di baris Agustus 2026; baris lain nilai tetap -> disimpan
```
dan di `layout_tables` ganti `stored = avail != "FORMULA"` dengan:
```python
            stored = avail != "FORMULA" or (sheet, key) in STORED_FORMULA
```

Run:
```bash
.venv/Scripts/python tools/export_schema.py
.venv/Scripts/python tools/generate_models.py
.venv/Scripts/python manage.py makemigrations finance
.venv/Scripts/python manage.py migrate
.venv/Scripts/python -m pytest
.venv/Scripts/python -m pytest -m slow importer
```
Expected: ekspor `tabel 34 | kolom tersimpan 604 | ...`; migrasi `Add field dihitung to bukukas`; semua uji cepat lulus; uji lambat importer `4 passed` (kesamaan setiap sel kini juga mencakup Dihitung).

- [ ] **Step 3: Commit**

```bash
git add tools/export_schema.py importer finance
git commit -m "fix: impor menyimpan kolom Dihitung buku kas (nilai tetap kecuali Agustus 2026)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 2: Angka emas dari Excel (alat COM + fixture JSON)

**Files:**
- Create: `tools/export_golden.py`, `dashboards/__init__.py`, `dashboards/tests/__init__.py`, `dashboards/tests/golden/jkt_golden.json` (hasil alat), `dashboards/tests/test_golden_fixture.py`

**Interfaces:**
- Produces: `dashboards/tests/golden/jkt_golden.json` dengan kunci:
  - `meta` {`workbook`, `sha256`, `hari_ini` "2026-09-30", `dibuat`}
  - `lists` {`bulan`, `program`, `tipe`, `mode`, `guru`, `level`, `kas_bulan`, `periode`} (tanpa "Semua")
  - `home` {`aktif`, `spp`, `off`, `kelas`, `kritis`, `bukti`, `sub_aktif`, `sub_spp`, `sub_off`, `sub_kelas`, `sub_kritis`, `sub_bukti`, `judul`, `off_raw` [baru, masih, perlu], `kelas_raw` [kursi_kosong, aktif]}
  - `students` {Student ID: [status sekarang, kode dipakai, guru dipakai]}
  - `off` {Off Record ID: [status, lama, tindak lanjut, tgl follow-up terakhir, tgl berikutnya, prioritas]}
  - `classes` {kode: [kapasitas, aktif, cuti, status kapasitas, status kelas, kursi kosong]}
  - `kas_rows` {ID Baris: [dihitung, s1, s2, s3, s4, b1, b2, b3, b4]}
  - `kas_bulanan` [[label, total, tertaut, belum tertaut]]
  - `laporan` [{`filter` {bulan, program, tipe, mode, guru}, `murid` [7], `spp` [7], `jumlah` [baru, off_baru, belum_bayar, daftar], `status` [5], `level` [[label, n]], `tipe` [[label, n]], `guru` [[label, n]], `tren` [[label pendek, aktif, cuti, off, baru]], `baris` {ID v1: [status, kelompok, ikut, off_baru, spp, status bayar]} (hanya skenario rinci)}]
  - `v4` [{`periode`, `status` [ACTIVE, ON LEAVE, OFF, PENDING], `aktivitas` [masuk, off baru, cuti baru, aktif kembali, sesi terlaksana, sesi batal, lead, follow-up, catatan akademik], `baris` {Student ID: status akhir periode}}]
  - Sel kosong = `""`, tanggal = `"YYYY-MM-DD"`, angka bulat = int.

- [ ] **Step 1: Alat angka emas**

`dashboards/__init__.py`, `dashboards/tests/__init__.py`: kosong.

`tools/export_golden.py`:
```python
"""Angka emas dari Excel (spesifikasi dasbor gelombang 1 §6). Jalankan dengan Python SISTEM yang punya pywin32 (bukan .venv):
    python tools/export_golden.py
Workbook di ..\\APP hanya dibaca: disalin ke folder sementara, dibuka di Excel tanpa makro & tanpa event, 'hari_ini' dikunci ke
30 Sep 2026, lalu tiap skenario dihitung ulang oleh Excel. Hasil: dashboards/tests/golden/jkt_golden.json (ID & angka, tanpa nama)."""
import datetime
import hashlib
import json
import shutil
import tempfile
import time
from pathlib import Path

import pythoncom
import win32com.client

WEB = Path(__file__).resolve().parent.parent
SRC = WEB.parent / "APP" / "SPI_STUDENT-SPP_APP_2026_09_v4.xlsm"
OUT = WEB / "dashboards" / "tests" / "golden" / "jkt_golden.json"
HARI_INI = datetime.datetime(2026, 9, 30)
SEMUA = "Semua"
XL_UP = -4162
XL_MANUAL = -4135


def norm(v):
    if v is None:
        return ""
    if hasattr(v, "year") and hasattr(v, "month") and hasattr(v, "day"):
        return datetime.date(v.year, v.month, v.day).isoformat()
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def retry(fn, tries=30):
    for i in range(tries):
        try:
            return fn()
        except pythoncom.com_error:
            if i == tries - 1:
                raise
            time.sleep(0.5)


def grid(ws, ref):
    v = retry(lambda: ws.Range(ref).Value)
    if not isinstance(v, tuple):
        return [[norm(v)]]
    return [[norm(x) for x in row] for row in v]


def col(ws, ref):
    return [r[0] for r in grid(ws, ref)]


def cell(ws, ref):
    return grid(ws, ref)[0][0]


def last_row(ws, column):
    return retry(lambda: ws.Cells(ws.Rows.Count, column).End(XL_UP).Row)


def until_blank(values):
    out = []
    for v in values:
        if v == "":
            break
        out.append(v)
    return out


def rows_by_key(ws, key_col, cols, first, last):
    keys = col(ws, f"{key_col}{first}:{key_col}{last}")
    data = [col(ws, f"{c}{first}:{c}{last}") for c in cols]
    return {k: [d[i] for d in data] for i, k in enumerate(keys) if k != ""}


def read_lists(wb):
    ls = wb.Worksheets("LISTS")
    return {"bulan": until_blank(col(ls, "A2:A40")), "program": until_blank(col(ls, "L3:L40")),
            "tipe": until_blank(col(ls, "M3:M40")), "mode": until_blank(col(ls, "N3:N40")), "guru": until_blank(col(ls, "O3:O200")),
            "level": until_blank(col(ls, "Q2:Q200")), "kas_bulan": until_blank(col(ls, "AL2:AL100")),
            "periode": until_blank(col(ls, "BI2:BI60"))}


def read_static(wb):
    home, off_c, kls = wb.Worksheets("HOME"), wb.Worksheets("C_OFF"), wb.Worksheets("C_KELAS")
    out = {"home": {k: cell(home, ref) for k, ref in (
        ("aktif", "B9"), ("spp", "F9"), ("off", "J9"), ("kelas", "B14"), ("kritis", "J14"), ("bukti", "F19"),
        ("sub_aktif", "B10"), ("sub_spp", "F10"), ("sub_off", "J10"), ("sub_kelas", "B15"), ("sub_kritis", "J15"),
        ("sub_bukti", "F20"), ("judul", "D4"))}}
    out["home"]["off_raw"] = [cell(off_c, "CA13"), cell(off_c, "CA17"), cell(off_c, "CA18")]
    out["home"]["kelas_raw"] = [cell(kls, "BD10"), cell(kls, "BD11")]
    sm = wb.Worksheets("STUDENT_MASTER")
    out["students"] = rows_by_key(sm, "A", ["X", "AH", "AN"], 6, last_row(sm, "A"))
    so = wb.Worksheets("STUDENT_OFF")
    out["off"] = rows_by_key(so, "AF", ["G", "S", "U", "V", "W", "Z"], 6, last_row(so, "AF"))
    cm = wb.Worksheets("CLASS_MASTER")
    classes = rows_by_key(cm, "B", ["K", "L", "M", "P", "Q"], 6, last_row(cm, "B"))
    n = last_row(kls, "A")
    kursi = dict(zip(col(kls, f"A2:A{n}"), col(kls, f"J2:J{n}")))
    out["classes"] = {k: v + [kursi.get(k, "")] for k, v in classes.items()}
    bk = wb.Worksheets("BUKU_KAS")
    out["kas_rows"] = rows_by_key(bk, "Z", ["M", "R", "S", "T", "U", "V", "W", "X", "Y"], 6, last_row(bk, "Z"))
    ck = wb.Worksheets("C_KAS")
    out["kas_bulanan"] = [[r[1], r[2], r[3], r[4]] for r in grid(ck, "T4:X40") if r[1] != ""]
    return out


def read_laporan(wb, lists, detail):
    ds, cd, ck, cl = (wb.Worksheets(n) for n in ("DASHBOARD", "C_DASH", "C_KAS", "C_LIST"))
    nlev, ntip, ngur = len(lists["level"]), len(lists["tipe"]), min(10, len(lists["guru"]))

    def mx(values):
        nums = [v for v in values if isinstance(v, (int, float))]
        return int(max(nums)) if nums else 0

    out = {"murid": [cell(ds, f"{c}9") for c in "BDFHJLN"], "spp": [cell(ds, f"{c}14") for c in "BDFHJLN"],
           "jumlah": [mx(col(cd, "R4:R327")), mx(col(cd, "S4:S327")), mx(col(ck, "L4:L327")), mx(col(cl, "A2:A325"))],
           "status": col(cd, "AG4:AG8"),
           "level": [r for r in grid(cd, f"AI4:AJ{3 + nlev}")] if nlev else [],
           "tipe": [r for r in grid(cd, f"AL4:AM{3 + ntip}")] if ntip else [],
           "guru": [r for r in grid(cd, f"AO4:AP{4 + ngur}")],
           "tren": [[r[1], r[2], r[3], r[4], r[5]] for r in grid(cd, "Y4:AD36")]}
    if detail:
        v1 = col(cd, "A4:A327")
        cols = [col(cd, f"{c}4:{c}327") for c in "DEKN"] + [col(ck, "J4:J327"), col(ck, "K4:K327")]
        out["baris"] = {k: [c[i] for c in cols] for i, k in enumerate(v1) if k != ""}
    return out


def read_v4(wb):
    ds, cm = wb.Worksheets("DASHBOARD"), wb.Worksheets("C_MURID")
    n = last_row(cm, "A")
    return {"status": [cell(ds, f"{c}139") for c in "BDFH"],
            "aktivitas": [cell(ds, f"{c}139") for c in "JLNP"] + [cell(ds, f"{c}143") for c in "HJLNP"],
            "baris": {k: v for k, v in zip(col(cm, f"A6:A{n}"), col(cm, f"R6:R{n}")) if k != ""}}


def scenarios(lists):
    last = lists["bulan"][-1]
    out = [dict(bulan=m) for m in lists["bulan"]]
    out += [dict(bulan=last, program=p) for p in lists["program"]]
    out += [dict(bulan=last, tipe=t) for t in lists["tipe"]]
    out += [dict(bulan=last, mode=m) for m in lists["mode"]]
    out += [dict(bulan=last, guru=g) for g in lists["guru"][:3]]
    pick = lambda xs, word: next((x for x in xs if word.lower() in str(x).lower()), xs[0])  # noqa: E731
    combo = dict(bulan=last, program=pick(lists["program"], "Development"), tipe=pick(lists["tipe"], "Partner"),
                 mode=pick(lists["mode"], "Onsite"), guru=lists["guru"][0])
    out += [combo, dict(bulan="Agu 2026", program=pick(lists["program"], "Development"))]
    full = [{"bulan": s["bulan"], "program": s.get("program", SEMUA), "tipe": s.get("tipe", SEMUA), "mode": s.get("mode", SEMUA),
             "guru": s.get("guru", SEMUA)} for s in out]
    plain = lambda b: {"bulan": b, "program": SEMUA, "tipe": SEMUA, "mode": SEMUA, "guru": SEMUA}  # noqa: E731
    detail = [plain(last), plain("Agu 2026"), plain("Jun 2024"), plain(lists["bulan"][0]), full[-2]]
    return full, detail


def main():
    tmp = Path(tempfile.mkdtemp(prefix="spi_golden_"))
    copy = tmp / SRC.name
    shutil.copy2(SRC, copy)
    pythoncom.CoInitialize()
    xl = win32com.client.DispatchEx("Excel.Application")
    wb = None
    try:
        xl.Visible, xl.DisplayAlerts, xl.ScreenUpdating, xl.EnableEvents = False, False, False, False
        xl.AutomationSecurity = 3                                   # makro tidak dijalankan
        wb = retry(lambda: xl.Workbooks.Open(str(copy), 0, False))
        xl.Calculation = XL_MANUAL
        st = wb.Worksheets("SETTINGS")
        keys = col(st, "D6:D80")
        row = 6 + keys.index("hari_ini")
        st.Range(f"B{row}").Value = HARI_INI
        t0 = time.time()
        retry(lambda: xl.CalculateFull())
        print(f"hitung penuh {time.time() - t0:.0f} dtk")
        lists = read_lists(wb)
        out = {"meta": {"workbook": SRC.name, "sha256": hashlib.sha256(SRC.read_bytes()).hexdigest(),
                        "hari_ini": HARI_INI.date().isoformat(), "dibuat": datetime.datetime.now().isoformat(timespec="seconds")},
               "lists": lists}
        out.update(read_static(wb))
        names = {k: wb.Names(k).RefersToRange for k in ("f_Bulan", "f_Program", "f_Tipe", "f_Mode", "f_Guru", "lap_Periode")}
        full, detail = scenarios(lists)
        out["laporan"] = []
        for i, f in enumerate(full, 1):
            for key, name in (("bulan", "f_Bulan"), ("program", "f_Program"), ("tipe", "f_Tipe"), ("mode", "f_Mode"), ("guru", "f_Guru")):
                names[name].Value = f[key]
            retry(lambda: xl.Calculate())
            out["laporan"].append({"filter": f, **read_laporan(wb, lists, f in detail)})
            print(f"laporan {i}/{len(full)} {f}")
        out["v4"] = []
        for per in ("Sep 2026", "Okt 2026", "Jan 2025"):
            names["lap_Periode"].Value = per
            retry(lambda: xl.Calculate())
            out["v4"].append({"periode": per, **read_v4(wb)})
            print("v4", per)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(out, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        print("tulis", OUT, OUT.stat().st_size, "byte")
    finally:
        if wb is not None:
            wb.Close(False)
        xl.Quit()
        del xl
        pythoncom.CoUninitialize()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
```

Run: `python tools/export_golden.py`
Expected: baris progres `laporan 1/…` sampai `v4 Jan 2025`, lalu `tulis …jkt_golden.json`. Excel lain milik pengguna tidak tersentuh (instans sendiri).

- [ ] **Step 2: Uji fixture (cepat)**

`dashboards/tests/test_golden_fixture.py`:
```python
"""Fixture angka emas = nilai Excel yang diketahui (HOME & DASHBOARD Sep 2026) dan tidak memuat nama murid."""
import json
from pathlib import Path

GOLDEN = json.loads((Path(__file__).parent / "golden" / "jkt_golden.json").read_text(encoding="utf-8"))
DEFAULT = {"bulan": "Sep 2026", "program": "Semua", "tipe": "Semua", "mode": "Semua", "guru": "Semua"}


def test_fixture_holds_the_known_excel_numbers():
    h = GOLDEN["home"]
    assert (h["aktif"], h["spp"], h["off"], h["kelas"], h["kritis"]) == (154, 69051000, 118, 106, 2)
    sep = next(s for s in GOLDEN["laporan"] if s["filter"] == DEFAULT)
    assert sep["murid"] == [157, 154, 3, 0, 3, 36, 9]
    assert sep["spp"][:2] == [69051000, 765383125]
    assert GOLDEN["meta"]["hari_ini"] == "2026-09-30"
    assert len(GOLDEN["lists"]["bulan"]) == 33 and GOLDEN["lists"]["bulan"][-1] == "Sep 2026"


def test_fixture_has_no_student_names():
    text = json.dumps(GOLDEN, ensure_ascii=False)
    assert "Abygail" not in text and "Alberto Jayaharto" not in text
```

Run: `.venv/Scripts/python -m pytest dashboards/tests/test_golden_fixture.py`
Expected: `2 passed`.

- [ ] **Step 3: Commit**

```bash
git add tools/export_golden.py dashboards
git commit -m "test: angka emas Excel (alat COM pada salinan workbook) untuk dasbor gelombang 1" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 3: App `dashboards` — data cabang, daftar, status murid

**Files:**
- Create: `dashboards/apps.py`, `dashboards/calc/__init__.py`, `dashboards/calc/base.py`, `dashboards/calc/status.py`
- Create: `dashboards/tests/helpers.py`, `dashboards/tests/test_status.py`, `dashboards/tests/test_golden.py`
- Modify: `spi_web/settings.py` (INSTALLED_APPS + `"dashboards"`)

**Interfaces:**
- Consumes: model Excel (Task 3 tahap 1A), `finance.BukuKas.dihitung` (Task 1), angka emas (Task 2).
- Produces (`dashboards.calc.base`): konstanta `MON_ID`, `PROG_ORDER`, `SEMUA`, `HIST_MONTHS`, `PERIOD_MONTHS`, `HIST_END`, `KAS_START`, `AGU_2026`, `JURNAL_TERSEMBUNYI`, `BELUM_DIPUTUSKAN`; helper `fold`, `same`, `label`, `short_label`, `day_label`, `yyyymm`, `period_code`, `parse_period`, `add_months`, `month_end`, `months_between`, `round_half_up`, `num`, `as_date`, `program_of`; kelas `BranchData(branch, today)` dengan `today`, `bulan_ini`, `setting(key, default)`, `memo(key, fn)`, baris `students`, `d_murid`, `d_bulan`, `events`, `offs`, `followups`, `classes`, `members`, `issues`, `bukti`, `kas`, `sesi`, `leads`, `academics`, `periodes`, `teachers`, indeks `bln_by_key`, `events_by_std`, `followups_by_std`, daftar `months_hist`, `programs`, `levels`, `tipes`, `modes`, `gurus`, `kas_months`, `period_open` (date|None), `last_import`.
- Produces (`dashboards.calc.status`): `kelompok(status)`, `event_terakhir(data, std, sampai)`, `status_sekarang(data, student)`, `semua_status_sekarang(data) -> {fold(std): status}`, `kode_dipakai(student)`, `guru_dipakai(student)`, `status_akhir_periode(data, student, mulai)`.
- Produces (`dashboards.tests.helpers`): `make_rows(model, branch, *dicts)`; (`dashboards.tests.test_golden`): fixture `jkt`, `data`, helper `assert_same(web, gold, what)`, `GOLDEN`.

- [ ] **Step 1: Uji yang gagal**

`dashboards/tests/helpers.py`:
```python
"""Membuat baris tabel Excel untuk uji: make_rows(Model, branch, {...}, {...}) -> row_no berurutan mulai 6."""


def make_rows(model, branch, *rows):
    return [model.objects.create(branch=branch, row_no=6 + i, **r) for i, r in enumerate(rows)]
```

`dashboards/tests/test_status.py`:
```python
import datetime

import pytest

from dashboards.calc.base import BranchData, label
from dashboards.calc.status import kelompok, kode_dipakai, semua_status_sekarang, status_akhir_periode, status_sekarang
from dashboards.tests.helpers import make_rows
from students.models import DBulan, DMurid, StatusEvent, StudentMaster

D = datetime.date


def test_group_follows_the_d_bulan_rule():
    assert [kelompok(s) for s in ("Aktif", "baru", "Rejoin", "Cuti", "OFF", "", None, "Lulus")] == \
        ["Aktif", "Aktif", "Aktif", "Cuti", "Off", "", "", ""]


@pytest.mark.django_db
def test_current_status_uses_the_latest_event_up_to_today(branch):
    a, b, c = make_rows(StudentMaster, branch, {"std": "STD-000001", "st_base": "ACTIVE"}, {"std": "STD-000002", "st_base": ""},
                        {"std": "STD-000003", "st_base": "OFF"})
    make_rows(StatusEvent, branch,
              {"eid": "EVT-000001", "std": "std-000001", "tgl": D(2026, 10, 3), "status": "ON LEAVE"},
              {"eid": "EVT-000002", "std": "STD-000001", "tgl": D(2026, 10, 3), "status": "OFF"},      # tanggal sama: baris kemudian menang
              {"eid": "EVT-000003", "std": "STD-000003", "tgl": D(2026, 12, 1), "status": "ACTIVE"})   # sesudah hari ini: diabaikan
    data = BranchData(branch, D(2026, 10, 5))
    assert [status_sekarang(data, s) for s in (a, b, c)] == ["OFF", "PENDING", "OFF"]
    assert semua_status_sekarang(data) == {"std-000001": "OFF", "std-000002": "PENDING", "std-000003": "OFF"}


@pytest.mark.django_db
def test_status_at_period_end_uses_events_then_history_then_baseline(branch):
    s1, s2 = make_rows(StudentMaster, branch, {"std": "STD-000001", "v1": "M001", "st_base": "ON LEAVE"},
                       {"std": "STD-000002", "v1": "M002", "st_base": "PENDING"})
    make_rows(DBulan, branch, {"key": "M001|202608", "v1": "M001", "bulan": D(2026, 8, 1), "status": "Baru"},
              {"key": "M002|202608", "v1": "M002", "bulan": D(2026, 8, 1), "status": "Lulus"})
    make_rows(StatusEvent, branch, {"eid": "EVT-000001", "std": "STD-000002", "tgl": D(2026, 10, 31), "status": "ACTIVE"})
    data = BranchData(branch, D(2026, 11, 2))
    assert [status_akhir_periode(data, s, D(2026, 8, 1)) for s in (s1, s2)] == ["ACTIVE", ""]
    assert [status_akhir_periode(data, s, D(2026, 10, 1)) for s in (s1, s2)] == ["ON LEAVE", "ACTIVE"]


def test_class_code_in_use_prefers_the_edit():
    assert kode_dipakai(StudentMaster(kode_in="P01", kode_read="F02")) == "P01"
    assert kode_dipakai(StudentMaster(kode_in="", kode_read="F02")) == "F02"


@pytest.mark.django_db
def test_lists_follow_the_excel_build(branch):
    make_rows(DMurid, branch, {"v1": "M1", "tipe_kelas_rapi": "Partner", "mode_rapi": "Onsite"},
              {"v1": "M2", "tipe_kelas_rapi": "Focus", "mode_rapi": "Online"}, {"v1": "M3", "tipe_kelas_rapi": "", "mode_rapi": ""})
    make_rows(DBulan, branch,
              {"key": "M1|202401", "grade": "Development 2.1", "guru": "Mr. Bram", "guru_asli": "bram"},
              {"key": "M2|202401", "grade": "Foundation 1.0", "guru": "Ms. Linda", "guru_asli": "linda"},
              {"key": "M3|202401", "grade": "Foundation 1.2", "guru": "Ms. Linda", "guru_asli": "Linda"},
              {"key": "M1|202402", "grade": "Development 2.1", "guru": "Mr. Bram", "guru_asli": "Bram"},
              {"key": "M2|202402", "grade": "Robotik", "guru": "Mr. Aldi", "guru_asli": ""})
    data = BranchData(branch, D(2026, 9, 30))
    assert data.programs == ["Foundation", "Development", "Robotik"]
    assert data.levels == ["Foundation 1.0", "Foundation 1.2", "Development 2.1", "Robotik"]
    assert (data.tipes, data.modes) == (["Focus", "Partner"], ["Online", "Onsite"])
    assert data.gurus == ["Mr. Bram", "Ms. Linda"]                     # seri 2-2: kemunculan pertama dulu; tanpa guru asli tidak dihitung
    assert [label(m) for m in data.months_hist][:2] == ["Jan 2024", "Feb 2024"] and len(data.months_hist) == 33
```

`dashboards/tests/test_golden.py`:
```python
"""Kesamaan dengan Excel tanpa toleransi (angka emas golden/jkt_golden.json). Lambat - mengimpor workbook Jakarta asli:
    .venv/Scripts/python -m pytest -m slow dashboards"""
import datetime
import hashlib
import json
from pathlib import Path

import pytest
from django.conf import settings

from branches.models import Branch
from dashboards.calc.base import BranchData, fold, label
from dashboards.calc.status import guru_dipakai, kode_dipakai, semua_status_sekarang
from importer.commit import commit_workbook
from importer.reader import read_workbook
from importer.schema import load_schema

pytestmark = pytest.mark.slow
GOLDEN = json.loads((Path(__file__).parent / "golden" / "jkt_golden.json").read_text(encoding="utf-8"))
TODAY = datetime.date.fromisoformat(GOLDEN["meta"]["hari_ini"])
SOURCE = settings.SPI_EXCEL_DIR / GOLDEN["meta"]["workbook"]


def norm(v):
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return [norm(x) for x in v]
    if isinstance(v, dict):
        return {k: norm(x) for k, x in v.items()}
    if isinstance(v, datetime.date):
        return v.isoformat()
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def assert_same(web, gold, what):
    web, gold = norm(web), norm(gold)
    if isinstance(gold, dict):
        missing, extra = sorted(set(gold) - set(web))[:10], sorted(set(web) - set(gold))[:10]
        diff = {k: (web[k], gold[k]) for k in gold if k in web and web[k] != gold[k]}
        assert (missing, extra, dict(list(diff.items())[:10])) == ([], [], {}), f"{what}: {len(diff)} beda"
    else:
        assert web == gold, what


@pytest.fixture(scope="module")
def jkt(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        branch = Branch.objects.create(code="SPI-JKT", name="SPI Jakarta", city="Jakarta", status="ACTIVE")
        commit_workbook(read_workbook(SOURCE), branch, None, replace=False, file_name=SOURCE.name, sha256="-")
    yield branch
    with django_db_blocker.unblock():
        for spec in load_schema():
            spec.model_class().objects.filter(branch=branch).delete()
        branch.delete()


@pytest.fixture
def data(jkt, db):
    return BranchData(jkt, TODAY)


def test_golden_numbers_belong_to_the_current_workbook():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == GOLDEN["meta"]["sha256"]


def test_lists(data):
    lists = GOLDEN["lists"]
    web = {"bulan": [label(m) for m in data.months_hist], "program": data.programs, "tipe": data.tipes, "mode": data.modes,
           "guru": data.gurus, "level": data.levels, "kas_bulan": [label(m) for m in data.kas_months]}
    assert_same(web, {k: lists[k] for k in web}, "daftar")


def test_students_now(data):
    st = semua_status_sekarang(data)
    web = {s.std: [st[fold(s.std)], kode_dipakai(s), guru_dipakai(s)] for s in data.students if s.std}
    assert_same(web, GOLDEN["students"], "status sekarang / kode / guru")
```

Run: `.venv/Scripts/python -m pytest dashboards/tests/test_status.py`
Expected: FAIL (`ModuleNotFoundError: No module named 'dashboards.calc'`).

- [ ] **Step 2: Implementasi**

`dashboards/apps.py`:
```python
from django.apps import AppConfig


class DashboardsConfig(AppConfig):
    name = "dashboards"
    verbose_name = "Dasbor"
```

Modify `spi_web/settings.py` — tambahkan `"dashboards",` sebagai baris terakhir `INSTALLED_APPS`.

`dashboards/calc/__init__.py`: kosong.

`dashboards/calc/base.py`:
```python
"""Data satu cabang untuk dasbor, dibaca sekali per permintaan. Aturan = rumus Excel v4 (spesifikasi dasbor gelombang 1 §3).
Perbandingan teks seperti Excel: tidak membedakan huruf besar/kecil (fold)."""
import datetime
from collections import Counter, defaultdict
from decimal import ROUND_HALF_UP, Decimal
from functools import cached_property

from audit.models import ImportLog
from branches.models import BranchSetting
from classes.models import ClassMaster, ClassMembers, Sesi
from finance.models import BuktiBayar, BukuKas, Periode
from masterdata.models import TeacherMaster
from quality.models import IssueUnit
from students.models import AcademicRecord, DBulan, DMurid, FollowUp, Lead, StatusEvent, StudentMaster, StudentOff

MON_ID = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
PROG_ORDER = ["Foundation", "Development", "Exploration", "Research"]
SEMUA = "Semua"
KAS_START = datetime.date(2024, 7, 1)
AGU_2026 = datetime.date(2026, 8, 1)
JURNAL_TERSEMBUNYI = "Jurnal Penerimaan (tersembunyi)"
BELUM_DIPUTUSKAN = "BELUM DIPUTUSKAN"


def fold(v):
    return "" if v is None else str(v).casefold()


def same(a, b):
    return fold(a) == fold(b)


def label(d):
    return f"{MON_ID[d.month - 1]} {d.year}"


def short_label(d):
    return f"{MON_ID[d.month - 1]} {str(d.year)[2:]}"


def day_label(d):
    return f"{d.day} {MON_ID[d.month - 1]} {d.year}"


def yyyymm(d):
    return f"{d.year}{d.month:02d}"


def period_code(d):
    return f"{d.year}-{d.month:02d}"


def parse_period(code):
    try:
        y, m = str(code).split("-")
        return datetime.date(int(y), int(m), 1)
    except (ValueError, TypeError):
        return None


def add_months(d, n):
    m = d.year * 12 + d.month - 1 + n
    return datetime.date(m // 12, m % 12 + 1, 1)


def month_end(d):
    return add_months(d, 1) - datetime.timedelta(days=1)


def months_between(start, end):
    """DATEDIF(start, end, "m"); None bila start > end (Excel: #NUM!)."""
    if start > end:
        return None
    n = (end.year - start.year) * 12 + end.month - start.month
    return n - 1 if end.day < start.day else n


def round_half_up(x):
    """ROUND(x, 0) Excel: setengah menjauhi nol."""
    return int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def num(v):
    """N() Excel: angka tetap angka, selain itu 0."""
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else 0


def as_date(v):
    if isinstance(v, datetime.datetime):
        return v.date()
    return v if isinstance(v, datetime.date) else None


def program_of(grade):
    """Program D_BULAN = LEFT(Level, FIND(" ", Level & " ") - 1)."""
    return ("" if grade is None else str(grade)).split(" ", 1)[0]


def _prog_rank(word):
    return PROG_ORDER.index(word) if word in PROG_ORDER else 99


HIST_START = datetime.date(2024, 1, 1)
HIST_MONTHS = [add_months(HIST_START, i) for i in range(33)]       # LISTS A: Jan 2024 ... Sep 2026 (tetap di Excel)
HIST_END = HIST_MONTHS[-1]                                          # LISTS!B34
PERIOD_MONTHS = [add_months(HIST_START, i) for i in range(48)]     # LISTS BI: Jan 2024 ... Des 2027


class BranchData:
    """Baris tabel Excel satu cabang (urutan sheet) dan nilai turunan yang dipakai banyak halaman."""

    months_hist = HIST_MONTHS

    def __init__(self, branch, today):
        self.branch = branch
        self.today = today
        self.bulan_ini = today.replace(day=1)
        self._memo = {}

    def memo(self, key, fn):
        if key not in self._memo:
            self._memo[key] = fn()
        return self._memo[key]

    def _rows(self, model):
        return list(model.objects.for_branch(self.branch).order_by("row_no", "pk"))

    @cached_property
    def settings(self):
        return {s.key: s.value for s in BranchSetting.objects.filter(branch=self.branch)}

    def setting(self, key, default=None):
        value = self.settings.get(key)
        return default if value in (None, "") else value

    @cached_property
    def students(self):
        return self._rows(StudentMaster)

    @cached_property
    def d_murid(self):
        return self._rows(DMurid)

    @cached_property
    def d_bulan(self):
        return self._rows(DBulan)

    @cached_property
    def events(self):
        return self._rows(StatusEvent)

    @cached_property
    def offs(self):
        return self._rows(StudentOff)

    @cached_property
    def followups(self):
        return self._rows(FollowUp)

    @cached_property
    def classes(self):
        return self._rows(ClassMaster)

    @cached_property
    def members(self):
        return self._rows(ClassMembers)

    @cached_property
    def issues(self):
        return self._rows(IssueUnit)

    @cached_property
    def bukti(self):
        return self._rows(BuktiBayar)

    @cached_property
    def kas(self):
        return self._rows(BukuKas)

    @cached_property
    def sesi(self):
        return self._rows(Sesi)

    @cached_property
    def leads(self):
        return self._rows(Lead)

    @cached_property
    def academics(self):
        return self._rows(AcademicRecord)

    @cached_property
    def periodes(self):
        return self._rows(Periode)

    @cached_property
    def teachers(self):
        return self._rows(TeacherMaster)

    @cached_property
    def bln_by_key(self):
        out = {}
        for r in self.d_bulan:
            out.setdefault(fold(r.key), r)                          # MATCH(...,0): baris pertama
        return out

    @cached_property
    def events_by_std(self):
        """ev_Ord hanya untuk baris ber-Student ID dan bertanggal."""
        out = defaultdict(list)
        for e in self.events:
            if e.std and as_date(e.tgl):
                out[fold(e.std)].append(e)
        return out

    @cached_property
    def followups_by_std(self):
        out = defaultdict(list)
        for f in self.followups:
            out[fold(f.std)].append(f)
        return out

    @cached_property
    def programs(self):
        return sorted({str(r.grade).split()[0] for r in self.d_bulan if r.grade}, key=lambda p: (_prog_rank(p), p))

    @cached_property
    def levels(self):
        return sorted({r.grade for r in self.d_bulan if r.grade}, key=lambda g: (_prog_rank(g.split()[0]), g))

    @cached_property
    def tipes(self):
        return sorted({m.tipe_kelas_rapi for m in self.d_murid if m.tipe_kelas_rapi})

    @cached_property
    def modes(self):
        return sorted({m.mode_rapi for m in self.d_murid if m.mode_rapi})

    @cached_property
    def gurus(self):
        """Guru (rapi) urut jumlah kemunculan; seri = kemunculan pertama menurut baris sheet (Counter.most_common)."""
        return [g for g, _ in Counter(r.guru for r in self.d_bulan if r.guru_asli).most_common()]

    @cached_property
    def kas_months(self):
        return sorted({as_date(r.bulan) for r in self.kas if as_date(r.bulan)})

    @cached_property
    def period_open(self):
        row = next((p for p in self.periodes if same(p.status, "OPEN")), None)
        return parse_period(row.per) if row else None

    @cached_property
    def last_import(self):
        return ImportLog.objects.for_branch(self.branch).order_by("-row_no").first()
```

`dashboards/calc/status.py`:
```python
"""Status murid: Kelompok D_BULAN, Status Sekarang (STUDENT_MASTER), status akhir periode (C_MURID), nilai 'dipakai' (spesifikasi §3.2)."""
from .base import HIST_END, as_date, fold, month_end, yyyymm

PETA_BULAN = {"aktif": "ACTIVE", "baru": "ACTIVE", "rejoin": "ACTIVE", "cuti": "ON LEAVE", "off": "OFF"}


def kelompok(status):
    s = fold(status)
    if s in ("aktif", "baru", "rejoin"):
        return "Aktif"
    if s == "cuti":
        return "Cuti"
    if s == "off":
        return "Off"
    return ""


def event_terakhir(data, std, sampai):
    """Status event dengan Urutan terbesar (tanggal efektif lalu baris) pada/sebelum `sampai`; None bila tidak ada."""
    best = None
    for e in data.events_by_std.get(fold(std), ()):
        tgl = as_date(e.tgl)
        if tgl <= sampai and (best is None or (tgl, e.row_no) > (as_date(best.tgl), best.row_no)):
            best = e
    return None if best is None else (best.status or "")


def status_sekarang(data, student):
    ev = event_terakhir(data, student.std, data.today)
    if ev is not None:
        return ev
    return student.st_base if student.st_base else "PENDING"


def semua_status_sekarang(data):
    return data.memo("st_now", lambda: {fold(s.std): status_sekarang(data, s) for s in data.students if s.std})


def kode_dipakai(student):
    return student.kode_in if student.kode_in else (student.kode_read or "")


def guru_dipakai(student):
    return student.guru_in if student.guru_in else (student.guru or "")


def status_akhir_periode(data, student, mulai):
    ev = event_terakhir(data, student.std, month_end(mulai))
    if ev is not None:
        return ev
    if mulai <= HIST_END:
        row = data.bln_by_key.get(fold(f"{student.v1}|{yyyymm(mulai)}"))
        return PETA_BULAN.get(fold(row.status if row else ""), "")
    return student.st_base or ""
```

- [ ] **Step 3: Jalankan uji**

Run:
```bash
.venv/Scripts/python -m pytest dashboards/tests/test_status.py
.venv/Scripts/python -m pytest -m slow dashboards/tests/test_golden.py
.venv/Scripts/python -m pytest
```
Expected: `5 passed`; uji emas `3 passed` (sha workbook, daftar, status sekarang/kode/guru); seluruh uji cepat lulus.

- [ ] **Step 4: Commit**

```bash
git add dashboards spi_web/settings.py
git commit -m "feat: dasbor - data cabang, daftar filter & status murid sama dengan Excel" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 4: Laporan bulanan murid (C_DASH)

**Files:**
- Create: `dashboards/calc/laporan.py`, `dashboards/tests/test_laporan.py`
- Modify: `dashboards/tests/test_golden.py` (uji laporan murid)

**Interfaces:**
- Consumes: `BranchData`, `fold`, `same`, `program_of`, `add_months`, `short_label`, `yyyymm`, `SEMUA`, `HIST_MONTHS` (Task 3); `kelompok` (Task 3).
- Produces (`dashboards.calc.laporan`):
  - `Filter(bulan: date, program="Semua", tipe="Semua", mode="Semua", guru="Semua")` (frozen dataclass), `Filter.lolos(row: DBulan) -> bool`, `Filter.as_dict(label_fn) -> dict`.
  - `Baris` (dataclass): `murid: DMurid`, `row: DBulan|None`, `status`, `kelompok`, `ikut: bool`, `off_baru: bool`; properti `v1`, `nama`, `std`, `program`, `level`, `guru`, `tipe`, `mode`, `kode_kelas`.
  - `baris_laporan(data, f) -> list[Baris]` (memo per filter).
  - `ringkasan_murid(data, f) -> dict` kunci `murid` [total, aktif, baru, rejoin, cuti, off, off_baru], `status` [[label, n]] ×5, `level`, `tipe`, `guru` [[label, n]], `tren` [[label pendek, aktif, cuti, off, baru]], `baru` list[Baris], `off_baru` list[Baris], `daftar` list[Baris].

- [ ] **Step 1: Uji yang gagal**

`dashboards/tests/test_laporan.py`:
```python
import datetime

import pytest

from dashboards.calc.base import BranchData
from dashboards.calc.laporan import Filter, baris_laporan, ringkasan_murid
from dashboards.tests.helpers import make_rows
from students.models import DBulan, DMurid

D = datetime.date
SEP, AGU = D(2026, 9, 1), D(2026, 8, 1)


def bulan(v1, b, status, grade="Development 2.1", guru="Mr. Bram", tipe="Partner", mode="Onsite"):
    return {"key": f"{v1}|{b:%Y%m}", "v1": v1, "bulan": b, "status": status, "grade": grade, "guru": guru, "guru_asli": guru,
            "tipe": tipe, "mode": mode}


@pytest.fixture
def data(branch):
    make_rows(DMurid, branch, *[{"v1": v, "nama": f"Murid {v}", "std": f"STD-00000{i}", "kode_kelas": f"P0{i}",
                                 "tipe_kelas_rapi": "Partner", "mode_rapi": "Onsite"} for i, v in enumerate("ABCDEF", 1)])
    make_rows(DBulan, branch,
              bulan("A", AGU, "Aktif"), bulan("A", SEP, "Off"),                                   # Off baru
              bulan("B", AGU, "Off"), bulan("B", SEP, "off"),                                     # Off lama
              bulan("C", SEP, "Baru", grade="Foundation 1.0", guru="Ms. Linda"),
              bulan("D", AGU, "Cuti"), bulan("D", SEP, "Rejoin", tipe="Focus", mode="Online"),
              bulan("E", SEP, "Cuti"),
              bulan("Z", SEP, "Aktif"))                                                          # tanpa D_MURID: hanya tren
    return BranchData(branch, D(2026, 9, 30))


@pytest.mark.django_db
def test_monthly_counts_follow_c_dash(data):
    r = ringkasan_murid(data, Filter(SEP))
    assert r["murid"] == [3, 2, 1, 1, 1, 2, 1]                          # total, aktif, baru, rejoin, cuti, off, off baru
    assert r["status"] == [["Aktif", 0], ["Baru", 1], ["Rejoin", 1], ["Cuti", 1], ["Off", 2]]   # status persis; 'off' = Off (tanpa beda huruf)
    assert [b.v1 for b in r["baru"]] == ["C"] and [b.v1 for b in r["off_baru"]] == ["A"]
    assert [b.v1 for b in r["daftar"]] == ["A", "B", "C", "D", "E"]     # F tidak punya baris bulan ini


@pytest.mark.django_db
def test_filters_use_the_month_row_and_ignore_case(data):
    r = ringkasan_murid(data, Filter(SEP, program="development", tipe="Partner"))
    assert [b.v1 for b in r["daftar"]] == ["A", "B", "E"]
    assert r["murid"][:2] == [1, 0]
    assert ringkasan_murid(data, Filter(SEP, guru="Ms. Linda"))["murid"] == [1, 1, 1, 0, 0, 0, 0]


@pytest.mark.django_db
def test_composition_and_trend(data):
    r = ringkasan_murid(data, Filter(SEP))
    assert r["level"] == [["Foundation 1.0", 1], ["Development 2.1", 1]]
    assert r["tipe"] == [["Partner", 1]]                                 # daftar tipe dari D_MURID; nilai dari baris bulan
    assert r["guru"][:2] == [["Mr. Bram", 1], ["Ms. Linda", 1]] and r["guru"][-1] == ["Lainnya / kosong", 0]
    tren = {t[0]: t[1:] for t in r["tren"]}
    assert len(r["tren"]) == 33 and tren["Sep 26"] == [3, 1, 2, 1] and tren["Agu 26"] == [1, 1, 1, 0]


@pytest.mark.django_db
def test_first_month_has_no_previous_month(data):
    rows = baris_laporan(data, Filter(D(2024, 1, 1)))
    assert all(not b.ikut and not b.off_baru for b in rows)
```

Tambahkan ke akhir `dashboards/tests/test_golden.py`:
```python


def scenario(f):
    from dashboards.calc.laporan import Filter
    bulan = {label(m): m for m in HIST_MONTHS}[f["bulan"]]
    return Filter(bulan, f["program"], f["tipe"], f["mode"], f["guru"])


@pytest.mark.parametrize("i", range(len(GOLDEN["laporan"])))
def test_laporan_murid(data, i):
    from dashboards.calc.laporan import ringkasan_murid
    gold = GOLDEN["laporan"][i]
    r = ringkasan_murid(data, scenario(gold["filter"]))
    web = {"murid": r["murid"], "status": [n for _l, n in r["status"]], "level": r["level"], "tipe": r["tipe"], "guru": r["guru"],
           "tren": r["tren"], "jumlah": [len(r["baru"]), len(r["off_baru"]), len(r["daftar"])]}
    want = {k: gold[k] for k in ("murid", "status", "level", "tipe", "guru", "tren")}
    want["jumlah"] = [gold["jumlah"][0], gold["jumlah"][1], gold["jumlah"][3]]
    assert_same(web, want, f"laporan {gold['filter']}")
```
dan ubah import di atas file menjadi `from dashboards.calc.base import HIST_MONTHS, BranchData, fold, label`.

Run: `.venv/Scripts/python -m pytest dashboards/tests/test_laporan.py`
Expected: FAIL (`ModuleNotFoundError: No module named 'dashboards.calc.laporan'`).

- [ ] **Step 2: Implementasi**

`dashboards/calc/laporan.py`:
```python
"""Laporan bulanan murid = C_DASH / C_LIST (spesifikasi §3.3). Baris = D_MURID (urutan sheet); data bulan = D_BULAN kunci 'ID v1|yyyymm'."""
from collections import Counter
from dataclasses import dataclass

from .base import HIST_MONTHS, SEMUA, add_months, as_date, fold, program_of, same, short_label, yyyymm
from .status import kelompok

STATUS_GRAFIK = ["Aktif", "Baru", "Rejoin", "Cuti", "Off"]
LAINNYA = "Lainnya / kosong"


@dataclass(frozen=True)
class Filter:
    bulan: object                       # date hari pertama bulan (salah satu HIST_MONTHS)
    program: str = SEMUA
    tipe: str = SEMUA
    mode: str = SEMUA
    guru: str = SEMUA

    def lolos(self, row):
        """Rumus K C_DASH / SUMPRODUCT tren: 'Semua' lolos; selain itu sama (tanpa beda huruf) dengan nilai baris bulan."""
        return all(same(want, SEMUA) or same(have, want) for want, have in (
            (self.program, program_of(row.grade)), (self.tipe, row.tipe), (self.mode, row.mode), (self.guru, row.guru)))


@dataclass
class Baris:
    murid: object
    row: object
    status: str
    kelompok: str
    ikut: bool
    off_baru: bool

    def _bulan(self, name):
        return (getattr(self.row, name) or "") if self.row else ""

    v1 = property(lambda self: self.murid.v1 or "")
    nama = property(lambda self: self.murid.nama or "")
    std = property(lambda self: self.murid.std or "")
    kode_kelas = property(lambda self: self.murid.kode_kelas or "")
    level = property(lambda self: self._bulan("grade"))
    program = property(lambda self: program_of(self._bulan("grade")))
    guru = property(lambda self: self._bulan("guru"))
    tipe = property(lambda self: self._bulan("tipe"))
    mode = property(lambda self: self._bulan("mode"))


def _row(data, v1, bulan):
    return data.bln_by_key.get(fold(f"{v1}|{yyyymm(bulan)}"))


def baris_laporan(data, f):
    def build():
        prev = add_months(f.bulan, -1) if f.bulan != HIST_MONTHS[0] else None
        out = []
        for m in data.d_murid:
            row = _row(data, m.v1, f.bulan)
            status = (row.status or "") if row else ""
            kel = kelompok(status) if row else ""
            ikut = row is not None and f.lolos(row)
            st_prev = ""
            if prev is not None:
                prow = _row(data, m.v1, prev)
                st_prev = (prow.status or "") if prow else ""
            off_baru = ikut and same(status, "Off") and st_prev != "" and not same(st_prev, "Off")
            out.append(Baris(m, row, status, kel, ikut, off_baru))
        return out
    return data.memo(("baris", f), build)


def _count(rows, key, wanted):
    return sum(1 for b in rows if same(key(b), wanted))


def ringkasan_murid(data, f):
    rows = [b for b in baris_laporan(data, f) if b.ikut]
    aktif = [b for b in rows if b.kelompok == "Aktif"]
    n_kel = Counter(b.kelompok for b in rows)
    murid = [n_kel["Aktif"] + n_kel["Cuti"], n_kel["Aktif"], _count(rows, lambda b: b.status, "Baru"),
             _count(rows, lambda b: b.status, "Rejoin"), n_kel["Cuti"], n_kel["Off"], sum(b.off_baru for b in rows)]
    gurus = data.gurus[:10]
    guru = [[g, _count(aktif, lambda b: b.guru, g)] for g in gurus]
    guru.append([LAINNYA, len(aktif) - sum(n for _g, n in guru)])
    return {
        "murid": murid,
        "status": [[s, _count(rows, lambda b: b.status, s)] for s in STATUS_GRAFIK],
        "level": [[lv, _count(aktif, lambda b: b.level, lv)] for lv in data.levels],
        "tipe": [[t, _count(aktif, lambda b: b.tipe, t)] for t in data.tipes],
        "guru": guru,
        "tren": tren(data, f),
        "baru": [b for b in rows if same(b.status, "Baru")],
        "off_baru": [b for b in rows if b.off_baru],
        "daftar": rows,
    }


def tren(data, f):
    """33 bulan, semua baris D_BULAN (juga yang tanpa D_MURID), filter selain bulan."""
    def build():
        per = {m: Counter() for m in HIST_MONTHS}
        for r in data.d_bulan:
            b = as_date(r.bulan)
            if b in per and f.lolos(r):
                per[b][kelompok(r.status)] += 1
                per[b]["baru"] += same(r.status, "Baru")
        return [[short_label(m), c["Aktif"], c["Cuti"], c["Off"], c["baru"]] for m, c in per.items()]
    return data.memo(("tren", f.program, f.tipe, f.mode, f.guru), build)
```

Catatan untuk pelaksana: `Baris` memakai `property(lambda ...)` di badan dataclass — atribut kelas yang bukan anotasi tidak menjadi field dataclass, jadi aman.

- [ ] **Step 3: Jalankan uji**

Run:
```bash
.venv/Scripts/python -m pytest dashboards/tests/test_laporan.py
.venv/Scripts/python -m pytest -m slow dashboards/tests/test_golden.py
```
Expected: `4 passed`; uji emas laporan lulus untuk semua skenario (±50 parametrize). Bila ada beda, pesan `assert_same` menunjukkan kunci & nilai web vs Excel — perbaiki aturan, bukan angka emas.

- [ ] **Step 4: Commit**

```bash
git add dashboards
git commit -m "feat: dasbor - laporan bulanan murid (KPI, komposisi, tren) sama dengan C_DASH" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 5: Buku kas & SPP (BUKU_KAS kolom rumus, C_KAS)

**Files:**
- Create: `dashboards/calc/kas.py`, `dashboards/tests/test_kas.py`
- Modify: `dashboards/calc/base.py` (helper `fixed`), `dashboards/tests/test_golden.py` (uji kas & SPP)

**Interfaces:**
- Consumes: `BranchData` (`kas`, `d_murid`, `students`, `kas_months`, `setting`), `KAS_START`, `AGU_2026`, `JURNAL_TERSEMBUNYI`, `BELUM_DIPUTUSKAN`, `fold`, `same`, `num`, `as_date`, `round_half_up`, `label`, `day_label` (Task 3); `Filter`, `baris_laporan`, `Baris` (Task 4).
- Produces (`dashboards.calc.base`): `fixed(x) -> str` (FIXED(x,0) Excel lokal Indonesia: "66.919.995").
- Produces (`dashboards.calc.kas`):
  - `KasRow` (dataclass): `row: BukuKas`, `dihitung: str`, `s: list[str]` (4), `b: list[float]` (4).
  - `kas_rows(data) -> list[KasRow]` (memo), `dihitung(data, row) -> str`, `bagian(data, row) -> (list[str], list[float])`.
  - `bulanan(data) -> list[[date, total, tertaut, belum]]` (bulan buku kas, urut).
  - `perlu_keputusan(data, bulan) -> bool`.
  - `spp_murid(data, bulan) -> dict[fold(std), float]` (memo; kosong bila bulan < Jul 2024).
  - `status_bayar(data, bulan, spp, kelompok) -> str`.
  - `ringkasan_spp(data, f) -> dict`: `spp` [diterima, ytd, aktif, sudah bayar, belum bayar, belum tertaut, tautan lemah] (angka atau "—"/"perlu keputusan"/teks), `per_baris` {id(Baris.murid): (spp, status bayar)}, `belum_bayar` list[Baris], `keputusan` bool.
  - `kas_terakhir(data) -> dict|None` kunci `bulan`, `total`, `tgl` (date|None), `prev_bulan` (date|None), `prev_total`.

- [ ] **Step 1: Uji yang gagal**

`dashboards/tests/test_kas.py`:
```python
import datetime

import pytest

from branches.models import BranchSetting
from dashboards.calc.base import BranchData, fixed
from dashboards.calc.kas import bagian, bulanan, dihitung, kas_terakhir, ringkasan_spp, spp_murid
from dashboards.calc.laporan import Filter
from dashboards.tests.helpers import make_rows
from finance.models import BukuKas
from students.models import DBulan, DMurid, StudentMaster

D = datetime.date
SEP, AGU, JUN24 = D(2026, 9, 1), D(2026, 8, 1), D(2024, 6, 1)


def kas(bulan, nominal, ss1="", sb1=None, ss2="", sb2=None, jenis="SPP", dihitung="YA", **extra):
    return {"bulan": bulan, "tgl": extra.pop("tgl", bulan), "jenis": jenis, "nominal": nominal, "dihitung": dihitung,
            "ss1": ss1, "sb1": sb1, "ss2": ss2, "sb2": sb2, "lid": extra.pop("lid", ""), **extra}


@pytest.fixture
def data(branch):
    BranchSetting.objects.create(branch=branch, key="jurnal_agu", value_text="Revisi Jurnal Penerimaan (dipakai Arus Kas)")
    make_rows(StudentMaster, branch, {"std": "STD-000001"}, {"std": "STD-000002"}, {"std": "STD-000003"}, {"std": "STD-000004"})
    make_rows(DMurid, branch, {"v1": "A", "nama": "Ani", "std": "STD-000001"}, {"v1": "B", "nama": "Budi", "std": "STD-000002"},
              {"v1": "C", "nama": "Budi", "std": "STD-000003"}, {"v1": "E", "nama": "Eko", "std": "STD-000004"})
    make_rows(DBulan, branch, *[{"key": f"{v}|202609", "v1": v, "bulan": SEP, "status": s}
                                for v, s in (("A", "Aktif"), ("B", "Aktif"), ("C", "Cuti"), ("E", "Aktif"))])
    make_rows(BukuKas, branch,
              kas(SEP, 600000, "STD-000001", 600000, tgl=D(2026, 9, 12), lid="BK-1"),
              kas(SEP, 500000, "std-000002", 250000, "STD-000003", 250000, yakin="Lemah - nama mirip", lid="BK-2"),
              kas(SEP, 300000, lid="BK-3"),                                                    # belum tertaut
              kas(SEP, 200000, "STD-000004", 200000, kor1="BUKAN MURID", lid="BK-4"),          # koreksi: bukan murid
              kas(SEP, 400000, "STD-000004", 400000, kor1="Budi [B]", kor2="Ani", lid="BK-5"),  # koreksi: dua murid
              kas(SEP, 999, "STD-000001", 999, jenis="Lainnya", lid="BK-6"),                   # bukan SPP
              kas(SEP, 777, "STD-000001", 777, dihitung="TIDAK", lid="BK-7"),                  # tidak dihitung
              kas(AGU, 100000, "STD-000001", 100000, versi="R · Revisi", dihitung="TIDAK", tgl=D(2026, 8, 30), lid="BK-8"),
              kas(AGU, 90000, "STD-000001", 90000, versi="T · Tersembunyi", dihitung="YA", lid="BK-9"),
              kas(D(2026, 1, 1), 50000, "STD-000001", 50000, lid="BK-10"))
    return BranchData(branch, D(2026, 9, 30))


def by_lid(data, lid):
    return next(r for r in data.kas if r.lid == lid)


@pytest.mark.django_db
def test_shares_follow_corrections(data):
    assert bagian(data, by_lid(data, "BK-1")) == (["STD-000001", "", "", ""], [600000, 0, 0, 0])
    assert bagian(data, by_lid(data, "BK-3")) == (["", "", "", ""], [0, 0, 0, 0])
    assert bagian(data, by_lid(data, "BK-4")) == (["", "", "", ""], [0, 0, 0, 0])
    assert bagian(data, by_lid(data, "BK-5")) == (["STD-000002", "STD-000001", "", ""], [200000, 200000, 0, 0])


@pytest.mark.django_db
def test_august_rows_follow_the_journal_choice(data, branch):
    assert [dihitung(data, by_lid(data, x)) for x in ("BK-8", "BK-9", "BK-1")] == ["YA", "TIDAK", "YA"]
    BranchSetting.objects.filter(branch=branch, key="jurnal_agu").update(value_text="jurnal penerimaan (tersembunyi)")
    fresh = BranchData(branch, D(2026, 9, 30))
    assert [dihitung(fresh, by_lid(fresh, x)) for x in ("BK-8", "BK-9")] == ["TIDAK", "YA"]


@pytest.mark.django_db
def test_monthly_totals_and_student_spp(data):
    rows = {b: [t, l, n] for b, t, l, n in bulanan(data)}
    assert rows[SEP] == [2000000, 1500000, 500000]
    assert rows[AGU] == [100000, 100000, 0]
    assert spp_murid(data, SEP) == {"std-000001": 800000, "std-000002": 450000, "std-000003": 250000}
    assert spp_murid(data, JUN24) == {}


@pytest.mark.django_db
def test_spp_kpis_for_the_report_month(data):
    r = ringkasan_spp(data, Filter(SEP))
    assert r["spp"] == [2000000, 2150000, 3, "2  ·  67%", 1, 1, 1]
    assert [b.v1 for b in r["belum_bayar"]] == ["E"]
    assert sorted(r["per_baris"].values()) == [(0, "Belum ada pembayaran"), (250000, "Sudah ada pembayaran"),
                                               (450000, "Sudah ada pembayaran"), (800000, "Sudah ada pembayaran")]


@pytest.mark.django_db
def test_months_before_the_cash_book_and_undecided_august(data, branch):
    early = ringkasan_spp(data, Filter(JUN24))
    assert early["spp"][:2] == ["—", "—"] and early["spp"][3:6] == ["—", "—", "—"]
    assert set(early["per_baris"].values()) == {(0, "(belum ada buku kas)")}
    BranchSetting.objects.filter(branch=branch, key="jurnal_agu").update(value_text="BELUM DIPUTUSKAN")
    agu = ringkasan_spp(BranchData(branch, D(2026, 9, 30)), Filter(AGU))
    assert agu["keputusan"] and agu["spp"][3:6] == ["perlu keputusan", "perlu keputusan", "—"]
    assert agu["belum_bayar"] == []


@pytest.mark.django_db
def test_last_cash_book_month(data):
    k = kas_terakhir(data)
    assert (k["bulan"], k["total"], k["tgl"], k["prev_bulan"], k["prev_total"]) == (SEP, 2000000, D(2026, 9, 12), AGU, 100000)
    assert fixed(66919995) == "66.919.995" and fixed(0) == "0" and fixed(1234.5) == "1.235"


@pytest.mark.django_db
def test_empty_branch_has_no_cash_book(other_branch):
    data = BranchData(other_branch, D(2026, 9, 30))
    assert kas_terakhir(data) is None and bulanan(data) == []
    assert ringkasan_spp(data, Filter(SEP))["spp"] == [0, 0, 0, 0, 0, 0, 0]
```

Penjelasan angka uji (Sep 2026): SPP & YA = BK-1..BK-5 → total 2.000.000; tertaut = 600.000 + 500.000 + 0 + 0 + 400.000 = 1.500.000.
Per murid: STD-1 = 600.000 + 200.000 (BK-5 bagian 2) = 800.000; STD-2 = 250.000 + 200.000; STD-3 = 250.000. YTD = Jan 50.000 + Agu 100.000 (R · dihitung YA) + Sep 2.000.000. Aktif = A, B, E (C Cuti); sudah bayar A, B → 2 · 67%; belum bayar E. Belum tertaut = baris tanpa Student ID 1 (BK-3, BK-4) − koreksi BUKAN MURID (BK-4) = 1. Tautan lemah = BK-2.

Tambahkan ke akhir `dashboards/tests/test_golden.py`:
```python


def test_kas_rows(data):
    from dashboards.calc.kas import kas_rows
    web = {k.row.lid: [k.dihitung, *k.s, *k.b] for k in kas_rows(data) if k.row.lid}
    assert_same(web, GOLDEN["kas_rows"], "BUKU_KAS Dihitung / Student ID / Bagian")


def test_kas_bulanan(data):
    from dashboards.calc.kas import bulanan
    assert_same([[label(b), t, l, n] for b, t, l, n in bulanan(data)], GOLDEN["kas_bulanan"], "C_KAS per bulan")


@pytest.mark.parametrize("i", range(len(GOLDEN["laporan"])))
def test_laporan_spp(data, i):
    from dashboards.calc.kas import ringkasan_spp
    gold = GOLDEN["laporan"][i]
    r = ringkasan_spp(data, scenario(gold["filter"]))
    assert_same({"spp": r["spp"], "belum_bayar": len(r["belum_bayar"])}, {"spp": gold["spp"][:7], "belum_bayar": gold["jumlah"][2]},
                f"SPP {gold['filter']}")


@pytest.mark.parametrize("i", [i for i, s in enumerate(GOLDEN["laporan"]) if "baris" in s])
def test_laporan_rows(data, i):
    from dashboards.calc.kas import ringkasan_spp
    from dashboards.calc.laporan import baris_laporan
    gold = GOLDEN["laporan"][i]
    f = scenario(gold["filter"])
    per = ringkasan_spp(data, f)["per_baris"]
    web = {b.v1: [b.status, b.kelompok, int(b.ikut), int(b.off_baru), *per[id(b.murid)]] for b in baris_laporan(data, f)}
    assert_same(web, gold["baris"], f"baris {gold['filter']}")
```

Run: `.venv/Scripts/python -m pytest dashboards/tests/test_kas.py`
Expected: FAIL (`ImportError: cannot import name 'fixed'`).

- [ ] **Step 2: Implementasi**

Tambahkan ke `dashboards/calc/base.py` di bawah `round_half_up`:
```python


def fixed(x):
    """FIXED(x, 0) Excel dengan pemisah ribuan Indonesia (titik)."""
    return f"{round_half_up(x):,}".replace(",", ".")
```

`dashboards/calc/kas.py`:
```python
"""Buku kas & SPP = kolom rumus BUKU_KAS dan C_KAS (spesifikasi §3.4)."""
from collections import Counter
from dataclasses import dataclass

from .base import AGU_2026, BELUM_DIPUTUSKAN, JURNAL_TERSEMBUNYI, KAS_START, as_date, fold, num, round_half_up, same
from .laporan import baris_laporan

BUKAN_MURID = "BUKAN MURID"
STRIP = "—"
KEPUTUSAN = "perlu keputusan"
SUDAH, BELUM, SEBELUM_KAS = "Sudah ada pembayaran", "Belum ada pembayaran", "(belum ada buku kas)"


@dataclass
class KasRow:
    row: object
    dihitung: str
    s: list
    b: list

    def masuk_spp(self, bulan=None):
        """Baris yang dijumlah C_KAS: Jenis SPP, Dihitung YA (dan bulan itu bila diberikan)."""
        return same(self.row.jenis, "SPP") and same(self.dihitung, "YA") and (bulan is None or as_date(self.row.bulan) == bulan)


def label_murid(data):
    """lst_MuridAll: nama D_MURID, '[ID v1]' ditambahkan bila nama kembar; posisi ke-i = Student ID baris ke-i STUDENT_MASTER."""
    def build():
        names = Counter(fold(m.nama) for m in data.d_murid)
        out = {}
        for m, s in zip(data.d_murid, data.students):
            lab = f"{m.nama} [{m.v1}]" if names[fold(m.nama)] > 1 else (m.nama or "")
            out.setdefault(fold(lab), s.std or "")
        return out
    return data.memo("label_murid", build)


def dihitung(data, row):
    """Nilai tersimpan; baris Agustus 2026 dua jurnal mengikuti SETTINGS jurnal_agu (versi 'T ·' tersembunyi, 'R ·' revisi)."""
    versi = fold(row.versi)
    if as_date(row.bulan) == AGU_2026 and versi[:1] in ("t", "r"):
        tersembunyi = same(data.setting("jurnal_agu", ""), JURNAL_TERSEMBUNYI)
        return "YA" if (versi[:1] == "t") == tersembunyi else "TIDAK"
    return row.dihitung or ""


def bagian(data, row):
    if row.kor1:
        labels = label_murid(data)
        s1 = "" if same(row.kor1, BUKAN_MURID) else labels.get(fold(row.kor1), "")
        s2 = "" if same(row.kor1, BUKAN_MURID) or not row.kor2 else labels.get(fold(row.kor2), "")
        s = [s1, s2, "", ""]
        nominal = num(row.nominal)
        b = [0 if not s1 else (nominal / 2 if s2 else nominal), 0 if not s2 else nominal / 2, 0, 0]
        return s, b
    s = [row.ss1 or "", row.ss2 or "", row.ss3 or "", row.ss4 or ""]
    b = [num(v) if sid else 0 for sid, v in zip(s, (row.sb1, row.sb2, row.sb3, row.sb4))]
    return s, b


def kas_rows(data):
    def build():
        out = []
        for r in data.kas:
            s, b = bagian(data, r)
            out.append(KasRow(r, dihitung(data, r), s, b))
        return out
    return data.memo("kas_rows", build)


def bulanan(data):
    out = []
    for bulan in data.kas_months:
        rows = [k for k in kas_rows(data) if k.masuk_spp(bulan)]
        total = sum(num(k.row.nominal) for k in rows)
        tertaut = sum(sum(k.b) for k in rows)
        out.append([bulan, total, tertaut, total - tertaut])
    return out


def perlu_keputusan(data, bulan):
    return bulan == AGU_2026 and same(data.setting("jurnal_agu", ""), BELUM_DIPUTUSKAN)


def spp_murid(data, bulan):
    def build():
        if bulan < KAS_START:
            return {}
        out = Counter()
        for k in kas_rows(data):
            if k.masuk_spp(bulan):
                for sid, amount in zip(k.s, k.b):
                    if sid:
                        out[fold(sid)] += amount
        return dict(out)
    return data.memo(("spp_murid", bulan), build)


def status_bayar(data, bulan, spp, kelompok):
    if bulan < KAS_START:
        return SEBELUM_KAS
    if perlu_keputusan(data, bulan):
        return KEPUTUSAN
    if spp > 0:
        return SUDAH
    return BELUM if kelompok == "Aktif" else ""


def _total(data, bulan):
    return sum(num(k.row.nominal) for k in kas_rows(data) if k.masuk_spp(bulan))


def ringkasan_spp(data, f):
    bulan, keputusan = f.bulan, perlu_keputusan(data, f.bulan)
    per_std = spp_murid(data, bulan)
    per_baris, belum = {}, []
    aktif = sudah = 0
    for b in baris_laporan(data, f):
        spp = 0 if bulan < KAS_START else per_std.get(fold(b.std), 0)
        st = status_bayar(data, bulan, spp, b.kelompok)
        per_baris[id(b.murid)] = (spp, st)
        if b.ikut and b.kelompok == "Aktif":
            aktif += 1
            sudah += spp > 0
        if b.ikut and st == BELUM:
            belum.append(b)
    sebelum = bulan < KAS_START
    rows = [k for k in kas_rows(data) if k.masuk_spp(bulan)]
    tertaut_kosong = sum(1 for k in rows if not k.s[0]) - sum(1 for k in rows if same(k.row.kor1, BUKAN_MURID))
    ytd = sum(t for m, t, _l, _n in bulanan(data) if m.year == bulan.year and m <= bulan)
    lemah = sum(1 for k in kas_rows(data) if fold(k.row.yakin).startswith("lemah") and not k.row.kor1)
    if sebelum:
        sudah_txt = belum_n = STRIP
    elif keputusan:
        sudah_txt = belum_n = KEPUTUSAN
    else:
        sudah_txt = 0 if aktif == 0 else f"{sudah}  ·  {round_half_up(sudah / aktif * 100)}%"
        belum_n = len(belum)
    return {
        "spp": [STRIP if sebelum else _total(data, bulan), STRIP if sebelum else ytd, aktif, sudah_txt, belum_n,
                STRIP if sebelum or keputusan else tertaut_kosong, lemah],
        "per_baris": per_baris,
        "belum_bayar": [] if keputusan or sebelum else belum,
        "keputusan": keputusan,
    }


def kas_terakhir(data):
    months = data.kas_months
    if not months:
        return None
    last = months[-1]
    prev = months[-2] if len(months) > 1 else None
    tgls = [as_date(r.tgl) for r in data.kas if as_date(r.bulan) == last and as_date(r.tgl)]
    return {"bulan": last, "total": _total(data, last), "tgl": max(tgls) if tgls else None,
            "prev_bulan": prev, "prev_total": _total(data, prev) if prev else 0}
```

Catatan aturan (dari rumus C_KAS): bulan sebelum Jul 2024 → status bayar "(belum ada buku kas)" dan bukan "Belum ada pembayaran", sehingga daftar belum bayar kosong; Agustus 2026 belum diputuskan → status "perlu keputusan" untuk semua baris, daftar belum bayar kosong (DASHBOARD menulis "Agustus 2026: perlu keputusan jurnal (SETTINGS)").

- [ ] **Step 3: Jalankan uji**

Run:
```bash
.venv/Scripts/python -m pytest dashboards/tests/test_kas.py
.venv/Scripts/python -m pytest -m slow dashboards/tests/test_golden.py
```
Expected: `7 passed`; uji emas kas_rows, kas_bulanan, laporan_spp (semua skenario), laporan_rows (5 skenario rinci) lulus.

- [ ] **Step 4: Commit**

```bash
git add dashboards
git commit -m "feat: dasbor - buku kas & SPP (Dihitung, bagian per murid, KPI) sama dengan C_KAS" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 6: Kelas, OFF, operasional v4, ringkasan Beranda

**Files:**
- Create: `dashboards/calc/kelas.py`, `dashboards/calc/off.py`, `dashboards/calc/operasional.py`, `dashboards/calc/beranda.py`
- Create: `dashboards/tests/test_kelas_off.py`, `dashboards/tests/test_beranda_calc.py`
- Modify: `dashboards/tests/test_golden.py` (kelas, OFF, HOME, periode v4)

**Interfaces:**
- Consumes: `BranchData`, helper base (Task 3, `fixed` Task 5); `semua_status_sekarang`, `status_sekarang`, `kode_dipakai`, `guru_dipakai`, `status_akhir_periode` (Task 3); `kas_terakhir` (Task 5).
- Produces:
  - `dashboards.calc.kelas`: `Kelas` (dataclass `row`, `kapasitas` angka|"" , `aktif`, `cuti`, `status_kapasitas`, `status_kelas`, `kursi_kosong`), `daftar_kelas(data) -> list[Kelas]`, `ringkasan_kelas(data) -> {"aktif", "kursi", "penuh", "melebihi"}`.
  - `dashboards.calc.off`: `MASIH_OFF`, `KEMBALI`, `PERLU`, `Off` (dataclass `row`, `status`, `lama` int|"", `aksi`, `fu_tgl` date|None, `fu_next` date|None, `prioritas`), `daftar_off(data) -> list[Off]`, `ringkasan_off(data) -> {"masih", "perlu", "baru"}`.
  - `dashboards.calc.operasional`: `kritis(data) -> int`, `teks_kritis(data, n) -> str`, `bukti(data) -> (belum, cek)`, `periode_v4(data, mulai: date) -> {"status": [4], "aktivitas": [9], "baris": {std: status}}`, `periode_default(data) -> date`.
  - `dashboards.calc.beranda`: `beranda(data) -> dict` (kunci `judul`, `aktif`, `sub_aktif`, `spp`, `spp_bulan`, `sub_spp`, `off`, `sub_off`, `kelas`, `sub_kelas`, `kritis`, `sub_kritis`, `bukti`, `sub_bukti`, `off_raw`, `kelas_raw`, `periode`, `impor`), `cari_murid(data, q, limit=20) -> list[dict]` (kunci `nama`, `status`, `kode`, `guru`, `std`).

- [ ] **Step 1: Uji yang gagal**

`dashboards/tests/test_kelas_off.py`:
```python
import datetime

import pytest

from branches.models import BranchSetting
from classes.models import ClassMaster, ClassMembers
from dashboards.calc.base import BranchData
from dashboards.calc.kelas import daftar_kelas, ringkasan_kelas
from dashboards.calc.off import KEMBALI, daftar_off, ringkasan_off
from dashboards.tests.helpers import make_rows
from students.models import FollowUp, StatusEvent, StudentMaster, StudentOff

D = datetime.date


@pytest.fixture
def setting(branch):
    def put(key, value):
        BranchSetting.objects.create(branch=branch, key=key, **BranchSetting.split_value(value))
    return put


@pytest.mark.django_db
def test_class_capacity_and_status(branch, setting):
    for k, v in (("F", 1), ("P", 4), ("G", 10), ("S", 20)):
        setting(k, v)
    make_rows(ClassMaster, branch, {"code": "P001", "tipe": "Partner"}, {"code": "f002", "tipe": "Focus"},
              {"code": "G003", "tipe": "Group"}, {"code": "P004", "tipe": "Partner"}, {"code": "X005", "tipe": "Partner"},
              {"code": "P006", "tipe": "Partner"})
    make_rows(StudentMaster, branch,
              *[{"std": f"STD-0000{i:02d}", "kode_read": "P001", "st_base": "ACTIVE"} for i in range(1, 4)],
              {"std": "STD-000010", "kode_read": "F002", "st_base": "ACTIVE"},
              {"std": "STD-000011", "kode_read": "x", "kode_in": "F002", "st_base": "ACTIVE"},
              {"std": "STD-000012", "kode_read": "G003", "st_base": "ON LEAVE"},
              {"std": "STD-000013", "kode_read": "X005", "st_base": "ACTIVE"})
    make_rows(ClassMembers, branch, {"code": "P004", "std": "STD-000099"})
    data = BranchData(branch, D(2026, 9, 30))
    got = {k.row.code: [k.kapasitas, k.aktif, k.cuti, k.status_kapasitas, k.status_kelas, k.kursi_kosong] for k in daftar_kelas(data)}
    assert got == {"P001": [4, 3, 0, "NORMAL", "ACTIVE", 1], "f002": [1, 2, 0, "OVER CAPACITY", "ACTIVE", 0],
                   "G003": [10, 0, 1, "KOSONG", "CUTI", 0], "P004": [4, 0, 0, "KOSONG", "INACTIVE", 0],
                   "X005": ["", 1, 0, "NORMAL", "ACTIVE", 0], "P006": [4, 0, 0, "KOSONG", "UNKNOWN", 0]}
    assert ringkasan_kelas(data) == {"aktif": 3, "kursi": 1, "penuh": 0, "melebihi": 1}


@pytest.mark.django_db
def test_off_status_follow_up_and_priority(branch, setting):
    setting("off_lama", 3)
    make_rows(StudentOff, branch,
              {"off_id": "OFF-1", "std": "STD-000001", "month": D(2026, 9, 1), "status_src": ""},          # baru off, belum follow-up
              {"off_id": "OFF-2", "std": "STD-000002", "month": D(2026, 6, 1), "status_src": "MASIH OFF"},  # 3 bln, belum follow-up
              {"off_id": "OFF-3", "std": "STD-000003", "month": D(2025, 1, 1), "status_src": ""},          # lama, ada tindak lanjut
              {"off_id": "OFF-4", "std": "STD-000004", "month": D(2026, 3, 1), "tgl": D(2026, 3, 20), "status_src": ""},  # aktif lagi
              {"off_id": "OFF-5", "std": "STD-000005", "month": D(2026, 2, 1), "status_src": "STATUS KOSONG (cek)"},
              {"off_id": "OFF-6", "std": "STD-000006", "month": D(2025, 5, 1), "status_src": ""},          # follow-up jatuh tempo
              {"off_id": "", "std": "STD-000007", "month": D(2026, 9, 1)})                                 # tanpa Off Record ID
    make_rows(StatusEvent, branch, {"eid": "EVT-1", "std": "STD-000004", "tgl": D(2026, 3, 19), "status": "ACTIVE"},
              {"eid": "EVT-2", "std": "STD-000004", "tgl": D(2026, 4, 2), "status": "ACTIVE"})
    make_rows(FollowUp, branch,
              {"fid": "FU-1", "std": "STD-000003", "tgl": D(2024, 12, 1), "aksi": "Kasus ditutup"},             # sebelum bulan Off: diabaikan
              {"fid": "FU-2", "std": "STD-000003", "tgl": D(2025, 2, 3), "aksi": "Hubungi orang tua"},
              {"fid": "FU-3", "std": "std-000003", "tgl": D(2025, 3, 4), "aksi": "", "next": D(2026, 10, 9)},
              {"fid": "FU-4", "std": "STD-000006", "tgl": D(2025, 6, 1), "aksi": "Telepon", "next": D(2026, 9, 30)})
    data = BranchData(branch, D(2026, 9, 30))
    got = {o.row.off_id: [o.status, o.lama, o.aksi, o.fu_tgl, o.fu_next, o.prioritas] for o in daftar_off(data)}
    assert got == {
        "OFF-1": ["MASIH OFF", 0, "", None, None, "MENDESAK"],
        "OFF-2": ["MASIH OFF", 3, "", None, None, "MINGGU INI"],
        "OFF-3": ["MASIH OFF", 20, "Hubungi orang tua", D(2025, 3, 4), D(2026, 10, 9), "PANTAU"],
        "OFF-4": [KEMBALI, "", "", None, None, "SELESAI"],
        "OFF-5": ["STATUS KOSONG (cek)", "", "", None, None, "PANTAU"],
        "OFF-6": ["MASIH OFF", 16, "Telepon", D(2025, 6, 1), D(2026, 9, 30), "HARI INI"],
    }
    assert ringkasan_off(data) == {"masih": 4, "perlu": 3, "baru": 1}
```

Penjelasan: OFF-4 kembali karena event ACTIVE 2 Apr ≥ tanggal Off 20 Mar (event 19 Mar terlalu awal tapi tetap cukup satu yang memenuhi). OFF-3: follow-up FU-1 sebelum bulan Off diabaikan; tindak lanjut terakhir yang terisi = FU-2; tanggal terakhir = FU-3; berikutnya 9 Okt > hari ini → bukan HARI INI; ada tindak lanjut → PANTAU.

`dashboards/tests/test_beranda_calc.py`:
```python
import datetime

import pytest

from audit.models import ImportLog
from branches.models import BranchSetting
from dashboards.calc.base import BranchData
from dashboards.calc.beranda import beranda, cari_murid
from dashboards.calc.operasional import bukti, kritis, periode_v4, teks_kritis
from dashboards.tests.helpers import make_rows
from finance.models import BuktiBayar, Periode
from quality.models import IssueUnit
from students.models import FollowUp, StatusEvent, StudentMaster

D = datetime.date


@pytest.mark.django_db
def test_critical_issues_and_payment_proofs(branch):
    make_rows(IssueUnit, branch, {"iid": "I1", "sev": "CRITICAL", "status": "OPEN"}, {"iid": "I2", "sev": "critical", "status": ""},
              {"iid": "I3", "sev": "CRITICAL", "status": "RESOLVED"}, {"iid": "I4", "sev": "CRITICAL", "status": "OPEN", "still": "CLEARED"},
              {"iid": "I5", "sev": "ERROR", "status": "OPEN"})
    make_rows(BuktiBayar, branch, {"bid": "B1", "ver": "Belum Diverifikasi"}, {"bid": "B2", "ver": "Tidak Cocok"},
              {"bid": "B3", "ver": "Perlu Klarifikasi"}, {"bid": "B4", "ver": "Verified"})
    data = BranchData(branch, D(2026, 9, 30))
    assert kritis(data) == 2 and bukti(data) == (1, 2)
    assert teks_kritis(data, 2) == "lihat TINDAKAN bagian 0" and teks_kritis(data, 0) == "tidak ada masalah kritis terbuka"
    BranchSetting.objects.create(branch=branch, key="jurnal_agu", value_text="BELUM DIPUTUSKAN")
    assert teks_kritis(BranchData(branch, D(2026, 9, 30)), 0) == "Jurnal Agustus 2026 perlu keputusan (SETTINGS)"


@pytest.mark.django_db
def test_operational_period_counts(branch):
    make_rows(StudentMaster, branch, {"std": "STD-000001", "st_base": "ACTIVE"}, {"std": "STD-000002", "st_base": "PENDING"})
    make_rows(StatusEvent, branch,
              {"eid": "E1", "std": "STD-000001", "tgl": D(2026, 10, 3), "status": "OFF", "jenis": "PERUBAHAN"},
              {"eid": "E2", "std": "STD-000009", "tgl": D(2026, 10, 9), "status": "ACTIVE", "jenis": "MASUK"},
              {"eid": "E3", "std": "STD-000008", "tgl": D(2026, 10, 9), "status": "ACTIVE", "jenis": "Aktif kembali (dari cuti)"})
    make_rows(FollowUp, branch, {"fid": "F1", "tgl": D(2026, 10, 1)}, {"fid": "F2", "tgl": D(2026, 9, 1)})
    data = BranchData(branch, D(2026, 10, 15))
    okt = periode_v4(data, D(2026, 10, 1))
    assert okt["status"] == [0, 0, 1, 1] and okt["baris"] == {"STD-000001": "OFF", "STD-000002": "PENDING"}
    assert okt["aktivitas"] == [1, 1, 0, 1, 0, 0, 0, 1, 0]


@pytest.mark.django_db
def test_home_summary_and_search(branch):
    make_rows(StudentMaster, branch, {"std": "STD-000001", "nama": "Ani Wijaya", "st_base": "ACTIVE", "kode_read": "P01", "guru": "Bram"},
              {"std": "STD-000002", "nama": "Budi", "st_base": "ON LEAVE"}, {"std": "STD-000003", "nama": "Wija", "st_base": ""})
    make_rows(Periode, branch, {"per": "2026-09", "label": "Sep 2026", "status": "OPEN"})
    make_rows(ImportLog, branch, {"batch": "IMP-JKT-20260930-01", "date": "2026-09-30 10:00", "file": "x.xlsm"})
    h = beranda(BranchData(branch, D(2026, 9, 30)))
    assert (h["aktif"], h["sub_aktif"]) == (1, "cuti 1  ·  pending 1  ·  status v4 (INPUT CENTER)")
    assert h["spp"] is None and h["sub_spp"] == "buku kas belum ada"
    assert h["judul"] == "Periode berjalan: Sep 2026   ·   riwayat DB Murid —   ·   buku kas —"
    assert (h["off"], h["sub_off"]) == (0, "0 perlu follow-up  ·  baru Off Sep 2026: 0")
    assert h["impor"].batch == "IMP-JKT-20260930-01"
    found = cari_murid(BranchData(branch, D(2026, 9, 30)), "wija")
    assert [(r["nama"], r["status"], r["kode"], r["guru"]) for r in found] == [("Ani Wijaya", "ACTIVE", "P01", "Bram"),
                                                                                ("Wija", "PENDING", "", "")]
    assert cari_murid(BranchData(branch, D(2026, 9, 30)), "  ") == []


@pytest.mark.django_db
def test_home_for_an_empty_branch(other_branch):
    h = beranda(BranchData(other_branch, D(2026, 9, 30)))
    assert (h["aktif"], h["off"], h["kelas"], h["kritis"], h["bukti"], h["spp"]) == (0, 0, 0, 0, 0, None)
    assert h["judul"].startswith("Periode berjalan: -") and h["impor"] is None
```

Tambahkan ke akhir `dashboards/tests/test_golden.py`:
```python


def test_classes(data):
    from dashboards.calc.kelas import daftar_kelas
    web = {k.row.code: [k.kapasitas, k.aktif, k.cuti, k.status_kapasitas, k.status_kelas, k.kursi_kosong]
           for k in daftar_kelas(data) if k.row.code}
    assert_same(web, GOLDEN["classes"], "CLASS_MASTER / C_KELAS")


def test_off(data):
    from dashboards.calc.off import daftar_off
    web = {o.row.off_id: [o.status, o.lama, o.aksi, o.fu_tgl, o.fu_next, o.prioritas] for o in daftar_off(data)}
    assert_same(web, GOLDEN["off"], "STUDENT_OFF")


def test_home(data):
    from dashboards.calc.beranda import beranda
    h = beranda(data)
    keys = ["aktif", "spp", "off", "kelas", "kritis", "bukti", "sub_aktif", "sub_spp", "sub_off", "sub_kelas", "sub_kritis",
            "sub_bukti", "judul", "off_raw", "kelas_raw"]
    assert_same({k: h[k] for k in keys}, {k: GOLDEN["home"][k] for k in keys}, "HOME")


@pytest.mark.parametrize("i", range(len(GOLDEN["v4"])))
def test_periode_v4(data, i):
    from dashboards.calc.operasional import periode_v4
    gold = GOLDEN["v4"][i]
    mulai = {label(m): m for m in PERIOD_MONTHS}[gold["periode"]]
    assert_same(periode_v4(data, mulai), {k: gold[k] for k in ("status", "aktivitas", "baris")}, f"v4 {gold['periode']}")
```
dan ubah import base di atas file menjadi `from dashboards.calc.base import HIST_MONTHS, PERIOD_MONTHS, BranchData, fold, label`.

Run: `.venv/Scripts/python -m pytest dashboards/tests/test_kelas_off.py dashboards/tests/test_beranda_calc.py`
Expected: FAIL (`ModuleNotFoundError: No module named 'dashboards.calc.kelas'`).

- [ ] **Step 2: Implementasi**

`dashboards/calc/kelas.py`:
```python
"""Kelas = kolom rumus CLASS_MASTER dan C_KELAS (spesifikasi §3.5)."""
from collections import Counter
from dataclasses import dataclass

from .base import fold, same
from .status import kode_dipakai, semua_status_sekarang

HURUF_KAPASITAS = ("F", "P", "G", "S")
TIPE_KURSI = ("partner", "group")


@dataclass
class Kelas:
    row: object
    kapasitas: object
    aktif: int
    cuti: int
    status_kapasitas: str
    status_kelas: str
    kursi_kosong: float


def kapasitas(data, code):
    """INDEX(set_CapNilai, MATCH(LEFT(kode, 1), set_CapHuruf, 0)); "" bila huruf tidak dikenal."""
    huruf = (code or "")[:1].upper()
    return data.setting(huruf, "") if huruf in HURUF_KAPASITAS else ""


def daftar_kelas(data):
    def build():
        st = semua_status_sekarang(data)
        aktif, cuti = Counter(), Counter()
        for s in data.students:
            if not s.std:
                continue
            status = fold(st[fold(s.std)])
            if status == "active":
                aktif[fold(kode_dipakai(s))] += 1
            elif status == "on leave":
                cuti[fold(kode_dipakai(s))] += 1
        berisi = {fold(m.code) for m in data.members if m.std}
        out = []
        for c in data.classes:
            k = fold(c.code)
            n, nc, cap = aktif[k], cuti[k], kapasitas(data, c.code)
            angka = isinstance(cap, (int, float))
            if n == 0:
                st_cap = "KOSONG"
            elif angka and n > cap:
                st_cap = "OVER CAPACITY"
            elif angka and n == cap:
                st_cap = "FULL"
            else:
                st_cap = "NORMAL"
            st_kls = "ACTIVE" if n > 0 else "CUTI" if nc > 0 else "INACTIVE" if k in berisi else "UNKNOWN"
            kursi = max(cap - n, 0) if st_kls == "ACTIVE" and fold(c.tipe) in TIPE_KURSI and angka else 0
            out.append(Kelas(c, cap, n, nc, st_cap, st_kls, kursi))
        return out
    return data.memo("kelas", build)


def ringkasan_kelas(data):
    rows = daftar_kelas(data)
    return {"aktif": sum(k.status_kelas == "ACTIVE" for k in rows), "kursi": sum(k.kursi_kosong for k in rows),
            "penuh": sum(k.status_kapasitas == "FULL" for k in rows),
            "melebihi": sum(k.status_kapasitas == "OVER CAPACITY" for k in rows)}
```

`dashboards/calc/off.py`:
```python
"""Murid OFF = kolom rumus STUDENT_OFF dan ringkasan C_OFF (spesifikasi §3.6). Hanya baris ber-Off Record ID."""
from dataclasses import dataclass

from .base import add_months, as_date, fold, months_between, num, same

MASIH_OFF = "MASIH OFF"
KEMBALI = "KEMBALI (aktif lagi · INPUT CENTER)"
PERLU = ("MENDESAK", "HARI INI", "MINGGU INI")


@dataclass
class Off:
    row: object
    status: str
    lama: object
    aksi: str
    fu_tgl: object
    fu_next: object
    prioritas: str


def _status(data, r):
    src = r.status_src or ""
    mulai = as_date(r.tgl) or as_date(r.month)
    if (src == "" or same(src, MASIH_OFF)) and mulai and any(
            same(e.status, "ACTIVE") and as_date(e.tgl) >= mulai for e in data.events_by_std.get(fold(r.std), ())):
        return KEMBALI
    return src or MASIH_OFF


def _prioritas(data, status, lama, aksi, fu_tgl, fu_next, month):
    if not same(status, MASIH_OFF):
        return "SELESAI" if fold(status).startswith("kembali") else "PANTAU"
    if same(aksi, "Kasus ditutup"):
        return "SELESAI"
    if fu_next and fu_next <= data.today:
        return "HARI INI"
    if not aksi and not fu_tgl and month and month >= add_months(data.bulan_ini, -1):
        return "MENDESAK"
    if not aksi and not fu_tgl and num(lama) <= num(data.setting("off_lama", 0)):
        return "MINGGU INI"
    return "PANTAU"


def daftar_off(data):
    def build():
        out = []
        for r in data.offs:
            if not r.off_id:
                continue
            month = as_date(r.month)
            status = _status(data, r)
            lama = ""
            if same(status, MASIH_OFF):
                lama = (months_between(month, data.bulan_ini) or 0) if month else 0
            fus = [f for f in data.followups_by_std.get(fold(r.std), ()) if month and as_date(f.tgl) and as_date(f.tgl) >= month]
            aksi = next((f.aksi for f in reversed(fus) if f.aksi), "")
            fu_tgl = max((as_date(f.tgl) for f in fus), default=None)
            fu_next = next((as_date(f.next) for f in reversed(fus) if f.next), None)
            out.append(Off(r, status, lama, aksi, fu_tgl, fu_next, _prioritas(data, status, lama, aksi, fu_tgl, fu_next, month)))
        return out
    return data.memo("off", build)


def ringkasan_off(data):
    rows = daftar_off(data)
    return {"masih": sum(same(o.status, MASIH_OFF) for o in rows), "perlu": sum(o.prioritas in PERLU for o in rows),
            "baru": sum(as_date(o.row.month) == data.bulan_ini for o in rows)}
```

`dashboards/calc/operasional.py`:
```python
"""Masalah kritis, bukti bayar, periode operasional v4 (spesifikasi §3.7)."""
from .base import BELUM_DIPUTUSKAN, as_date, fold, parse_period, period_code, same
from .status import status_akhir_periode

STATUS_V4 = ["ACTIVE", "ON LEAVE", "OFF", "PENDING"]


def kritis(data):
    return sum(1 for i in data.issues if same(i.sev, "CRITICAL") and not same(i.status, "RESOLVED")
               and not same(i.status, "CLOSED") and not same(i.still, "CLEARED"))


def teks_kritis(data, n):
    if same(data.setting("jurnal_agu", ""), BELUM_DIPUTUSKAN):
        return "Jurnal Agustus 2026 perlu keputusan (SETTINGS)"
    return "tidak ada masalah kritis terbuka" if n == 0 else "lihat TINDAKAN bagian 0"


def bukti(data):
    belum = sum(1 for b in data.bukti if same(b.ver, "Belum Diverifikasi"))
    cek = sum(1 for b in data.bukti if same(b.ver, "Tidak Cocok") or same(b.ver, "Perlu Klarifikasi"))
    return belum, cek


def _per(tgl):
    d = as_date(tgl)
    return period_code(d) if d else ""


def periode_default(data):
    return data.period_open or data.bulan_ini


def periode_v4(data, mulai):
    kode = period_code(mulai)
    baris = {s.std: status_akhir_periode(data, s, mulai) for s in data.students if s.std}
    ev = [e for e in data.events if _per(e.tgl) == kode]
    sesi = [s for s in data.sesi if same(s.per, kode)]
    return {
        "status": [sum(same(v, s) for v in baris.values()) for s in STATUS_V4],
        "aktivitas": [
            sum(same(e.jenis, "MASUK") for e in ev), sum(same(e.status, "OFF") for e in ev),
            sum(same(e.status, "ON LEAVE") for e in ev), sum(fold(e.jenis).startswith("aktif kembali") for e in ev),
            sum(same(s.status, "REALIZED") or same(s.status, "MAKE-UP") for s in sesi), sum(same(s.status, "CANCELLED") for s in sesi),
            sum(_per(x.tgl) == kode for x in data.leads), sum(_per(x.tgl) == kode for x in data.followups),
            sum(_per(x.tgl) == kode for x in data.academics)],
        "baris": baris,
    }
```

`periode_v4` memakai kamus `baris` per Student ID; Student ID kembar di STUDENT_MASTER dihitung sekali (C_MURID juga satu baris per murid). Jika uji emas menunjukkan beda karena ID kembar, hitung status dari daftar (bukan kamus) — catat sebagai ruling.

`dashboards/calc/beranda.py`:
```python
"""Ringkasan HOME (spesifikasi §4 Beranda) — teks keterangan sama dengan rumus HOME Excel."""
from collections import Counter

from .base import HIST_END, day_label, fixed, fold, label, month_end, same
from .kas import kas_terakhir
from .kelas import ringkasan_kelas
from .off import ringkasan_off
from .operasional import bukti, kritis, teks_kritis
from .status import guru_dipakai, kode_dipakai, semua_status_sekarang

SEP = "  ·  "
SEP_JUDUL = "   ·   "


def _periode_label(data):
    row = next((p for p in data.periodes if same(p.status, "OPEN")), None)
    return (row.label or "-") if row else "-"


def beranda(data):
    st = semua_status_sekarang(data)
    n = Counter(fold(st[fold(s.std)]) for s in data.students if s.std)
    kas = kas_terakhir(data)
    off, kelas = ringkasan_off(data), ringkasan_kelas(data)
    n_kritis = kritis(data)
    belum, cek = bukti(data)
    if kas is None:
        sub_spp, kas_judul = "buku kas belum ada", "buku kas —"
    else:
        tgl = day_label(kas["tgl"]) if kas["tgl"] else label(kas["bulan"])
        lengkap = "" if kas["tgl"] and kas["tgl"] >= month_end(kas["bulan"]) else " (belum lengkap)"
        sub_spp = f"buku kas s/d {tgl}{lengkap}"
        if kas["prev_bulan"]:
            sub_spp += f"{SEP}{label(kas['prev_bulan'])}: Rp {fixed(kas['prev_total'])}"
        kas_judul = f"buku kas s/d {tgl}"
    riwayat = f"riwayat DB Murid s/d {label(HIST_END)}" if data.d_bulan else "riwayat DB Murid —"
    periode = _periode_label(data)
    return {
        "judul": f"Periode berjalan: {periode}{SEP_JUDUL}{riwayat}{SEP_JUDUL}{kas_judul}",
        "periode": periode,
        "aktif": n["active"],
        "sub_aktif": f"cuti {n['on leave']}{SEP}pending {n['pending']}{SEP}status v4 (INPUT CENTER)",
        "spp": kas["total"] if kas else None,
        "spp_bulan": kas["bulan"] if kas else None,
        "sub_spp": sub_spp,
        "off": off["masih"],
        "sub_off": f"{off['perlu']} perlu follow-up{SEP}baru Off {label(data.bulan_ini)}: {off['baru']}",
        "off_raw": [off["baru"], off["masih"], off["perlu"]],
        "kelas": kelas["aktif"],
        "sub_kelas": f"penuh {kelas['penuh']}{SEP}kursi kosong {fixed(kelas['kursi'])}{SEP}melebihi {kelas['melebihi']}",
        "kelas_raw": [kelas["kursi"], kelas["aktif"]],
        "kritis": n_kritis,
        "sub_kritis": teks_kritis(data, n_kritis),
        "bukti": belum,
        "sub_bukti": f"bukti bayar dari INPUT CENTER{SEP}perlu klarifikasi: {cek}",
        "impor": data.last_import,
    }


def cari_murid(data, q, limit=20):
    q = fold(q).strip()
    if not q:
        return []
    st = semua_status_sekarang(data)
    out = []
    for s in data.students:
        if s.std and q in fold(s.nama):
            out.append({"nama": s.nama or "", "status": st[fold(s.std)], "kode": kode_dipakai(s), "guru": guru_dipakai(s), "std": s.std})
            if len(out) >= limit:
                break
    return out
```

Catatan: kursi kosong di teks HOME memakai angka biasa Excel (`&C_KELAS!BD10&`); `fixed()` hanya menambah pemisah ribuan — untuk 184 hasilnya sama ("184"). Ruling bila angka ≥ 1000: tampilan web memakai pemisah ribuan.

- [ ] **Step 3: Jalankan uji**

Run:
```bash
.venv/Scripts/python -m pytest dashboards
.venv/Scripts/python -m pytest -m slow dashboards/tests/test_golden.py
```
Expected: semua uji cepat dashboards lulus; uji emas classes, off, home, periode_v4 (3) lulus.

- [ ] **Step 4: Commit**

```bash
git add dashboards
git commit -m "feat: dasbor - kelas, OFF, periode v4 & ringkasan Beranda sama dengan Excel" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 7: Sistem desain gaya B (token, huruf, ikon, komponen, grafik)

**Files:**
- Modify: `package.json` (via npm), `assets/copy-vendor.mjs`, `assets/app.css`, `templates/base.html`, `templates/base_auth.html`, `core/nav.py`
- Create: `static/vendor/chart.umd.min.js`, `static/vendor/tabler/…`, `static/vendor/fonts/…` (hasil `npm run vendor`), `static/js/dashboards.js`
- Create: `templates/components/kpi_card.html`, `templates/components/chart_card.html`, `templates/components/status_badge.html`
- Create: `dashboards/templatetags/__init__.py`, `dashboards/templatetags/spi.py`, `core/tests/test_design.py`

**Interfaces:**
- Consumes: `fixed` (Task 5).
- Produces:
  - Kelas CSS: `.tone-murid|spp|off|kelas|kritis|akad|soon` (variabel `--t50 --t100 --t600 --t800`), `.kpi`, `.kpi-head`, `.kpi-label`, `.kpi-icon`, `.kpi-value`, `.kpi-sub`, `.kpi-link`, `.kpi-soon`, `.section-title`, `.chip`, `.chip-active`, `.status-badge` + `.st-baik|perhatian|serius|kritis|netral`, `.table-wrap`, `.data-table`.
  - Komponen `{% include "components/kpi_card.html" with tone= icon= label= value= sub= href= link_text= soon= hx=%}`; `{% include "components/chart_card.html" with chart=<dict> %}` (dict: `id`, `title`, `type` "bar"|"line", `labels`, `series` [{`label`, `data`, `color`}], `horizontal`, `stacked`, `money`, `links` list URL|None, `note`); `{% include "components/status_badge.html" with status= %}`.
  - Filter templat (`{% load spi %}`): `angka` (titik ribuan; teks dibiarkan), `rp` ("Rp 1.234" untuk angka; teks dibiarkan), `tone_status` (status → `baik|perhatian|serius|kritis|netral`), `ikon_status`.
  - `static/js/dashboards.js`: `SPICharts.init(root)` membaca `<canvas data-chart="id">` + `<script type="application/json" id="id">`; otomatis saat `DOMContentLoaded` dan `htmx:afterSettle`.
  - Palet grafik tetap `CHART_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]` di `dashboards/calc/base.py`.

- [ ] **Step 1: Uji yang gagal**

`core/tests/test_design.py`:
```python
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string

from dashboards.templatetags.spi import angka, ikon_status, rp, tone_status

STATIC = Path(settings.BASE_DIR) / "static"


def test_local_assets_are_present():
    for rel in ("vendor/chart.umd.min.js", "vendor/tabler/tabler-icons.min.css", "vendor/fonts/plus-jakarta-sans-latin-400-normal.woff2",
                "vendor/fonts/plus-jakarta-sans-latin-700-normal.woff2", "js/dashboards.js"):
        assert (STATIC / rel).is_file(), rel
    assert any((STATIC / "vendor/tabler/fonts").glob("tabler-icons.woff2*"))
    css = (STATIC / "css/app.css").read_text(encoding="utf-8")
    assert ".kpi" in css and "Plus Jakarta Sans" in css and ".tone-spp" in css


def test_number_filters_follow_indonesian_format():
    assert (angka(1234567), angka(1234.5), angka("—"), angka(None)) == ("1.234.567", "1.235", "—", "")
    assert (rp(69051000), rp("perlu keputusan"), rp(None)) == ("Rp 69.051.000", "perlu keputusan", "—")
    assert [tone_status(s) for s in ("Aktif", "Baru", "Rejoin", "Cuti", "Off", "ACTIVE", "ON LEAVE", "OFF", "PENDING", "x")] == \
        ["baik", "baik", "baik", "perhatian", "kritis", "baik", "perhatian", "kritis", "serius", "netral"]
    assert ikon_status("Off") == "circle-x" and ikon_status("Aktif") == "circle-check"


def test_kpi_card_renders_value_or_soon():
    html = render_to_string("components/kpi_card.html", {"tone": "spp", "icon": "cash", "label": "SPP diterima", "value": "Rp 1",
                                                          "sub": "buku kas", "href": "/laporan/"})
    assert "tone-spp" in html and "ti-cash" in html and "Rp 1" in html and 'href="/laporan/"' in html
    soon = render_to_string("components/kpi_card.html", {"tone": "kritis", "icon": "list-check", "label": "Perlu tindakan", "soon": True})
    assert "kpi-soon" in soon and "menyusul" in soon and "tone-soon" in soon


def test_chart_card_has_data_table_and_legend():
    from dashboards.calc.base import chart

    c = chart("c-status", "Status murid", ["Aktif", "Off"], [("Murid", [5, 2])], links=["/laporan/?daftar=aktif", None])
    html = render_to_string("components/chart_card.html", {"chart": c})
    assert 'data-chart="c-status"' in html and 'id="c-status"' in html and "<table" in html
    assert 'href="/laporan/?daftar=aktif"' in html and "Status murid" in html and c["series"][0]["color"] == "#2a78d6"
```

Run: `.venv/Scripts/python -m pytest core/tests/test_design.py`
Expected: FAIL (`ModuleNotFoundError: No module named 'dashboards.templatetags'`).

- [ ] **Step 2: Aset lokal**

Run:
```bash
npm install --save-dev @fontsource/plus-jakarta-sans @tabler/icons-webfont chart.js
```

Ganti `assets/copy-vendor.mjs`:
```js
import { copyFileSync, cpSync, existsSync, mkdirSync } from "node:fs";

mkdirSync("static/vendor/fonts", { recursive: true });
mkdirSync("static/vendor/tabler", { recursive: true });
copyFileSync("node_modules/htmx.org/dist/htmx.min.js", "static/vendor/htmx.min.js");
copyFileSync("node_modules/alpinejs/dist/cdn.min.js", "static/vendor/alpine.min.js");
const chart = ["node_modules/chart.js/dist/chart.umd.min.js", "node_modules/chart.js/dist/chart.umd.js"].find(existsSync);
copyFileSync(chart, "static/vendor/chart.umd.min.js");
for (const w of [400, 500, 600, 700, 800]) {
  const f = `plus-jakarta-sans-latin-${w}-normal.woff2`;
  copyFileSync(`node_modules/@fontsource/plus-jakarta-sans/files/${f}`, `static/vendor/fonts/${f}`);
}
copyFileSync("node_modules/@tabler/icons-webfont/dist/tabler-icons.min.css", "static/vendor/tabler/tabler-icons.min.css");
cpSync("node_modules/@tabler/icons-webfont/dist/fonts", "static/vendor/tabler/fonts", { recursive: true });
console.log("vendor: htmx, alpine, chart.js, Plus Jakarta Sans, Tabler Icons disalin ke static/vendor");
```

Run: `npm run vendor`
Expected: `vendor: htmx, alpine, chart.js, Plus Jakarta Sans, Tabler Icons disalin ke static/vendor`. Bila nama berkas berbeda di versi terpasang (`ls node_modules/@tabler/icons-webfont/dist`), sesuaikan jalur sumber (catat sebagai ruling); jalur tujuan tetap.

- [ ] **Step 3: Token & komponen CSS**

Ganti isi `assets/app.css` dengan:
```css
@import "tailwindcss";
@source "../templates";
@source "../core/templates";
@source "../accounts/templates";
@source "../importer/templates";
@source "../branches/templates";
@source "../dashboards/templates";
@source "../static/js";

@font-face { font-family: "Plus Jakarta Sans"; font-style: normal; font-weight: 400; font-display: swap; src: url("../vendor/fonts/plus-jakarta-sans-latin-400-normal.woff2") format("woff2"); }
@font-face { font-family: "Plus Jakarta Sans"; font-style: normal; font-weight: 500; font-display: swap; src: url("../vendor/fonts/plus-jakarta-sans-latin-500-normal.woff2") format("woff2"); }
@font-face { font-family: "Plus Jakarta Sans"; font-style: normal; font-weight: 600; font-display: swap; src: url("../vendor/fonts/plus-jakarta-sans-latin-600-normal.woff2") format("woff2"); }
@font-face { font-family: "Plus Jakarta Sans"; font-style: normal; font-weight: 700; font-display: swap; src: url("../vendor/fonts/plus-jakarta-sans-latin-700-normal.woff2") format("woff2"); }
@font-face { font-family: "Plus Jakarta Sans"; font-style: normal; font-weight: 800; font-display: swap; src: url("../vendor/fonts/plus-jakarta-sans-latin-800-normal.woff2") format("woff2"); }

@theme {
  --font-sans: "Plus Jakarta Sans", ui-sans-serif, system-ui, sans-serif;
  --color-brand-50: #eef4ff;
  --color-brand-100: #dce8ff;
  --color-brand-500: #176df8;
  --color-brand-600: #0f5fe0;
  --color-brand-700: #0b4bb3;
  --color-brand-900: #041a5a;
  --color-st-baik: #0ca30c;
  --color-st-perhatian: #fab219;
  --color-st-serius: #ec835a;
  --color-st-kritis: #d03b3b;
}

[x-cloak] { display: none !important; }

/* Warna topik gaya B: 50 latar, 100 garis/ikon, 600 aksen, 800 teks */
.tone-murid  { --t50: #e6f1fb; --t100: #b5d4f4; --t600: #185fa5; --t800: #0c447c; }
.tone-spp    { --t50: #eaf3de; --t100: #c0dd97; --t600: #3b6d11; --t800: #27500a; }
.tone-off    { --t50: #faeeda; --t100: #fac775; --t600: #854f0b; --t800: #633806; }
.tone-kelas  { --t50: #eeedfe; --t100: #cecbf6; --t600: #534ab7; --t800: #3c3489; }
.tone-kritis { --t50: #fcebeb; --t100: #f7c1c1; --t600: #a32d2d; --t800: #791f1f; }
.tone-akad   { --t50: #e1f5ee; --t100: #9fe1cb; --t600: #0f6e56; --t800: #085041; }
.tone-soon   { --t50: #f8fafc; --t100: #cbd5e1; --t600: #64748b; --t800: #475569; }

@layer components {
  .btn { @apply inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50 disabled:cursor-not-allowed disabled:opacity-50; }
  .btn-primary { @apply bg-brand-600 text-white shadow-sm hover:bg-brand-700; }
  .btn-secondary { @apply border border-slate-300 bg-white text-slate-700 hover:bg-slate-50; }
  .btn-danger { @apply bg-red-600 text-white hover:bg-red-700; }
  .card { @apply rounded-xl border border-slate-200 bg-white shadow-sm; }
  .badge { @apply inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold; }
  .form label { @apply mb-1 block text-sm font-medium text-slate-700; }
  .form input:not([type=checkbox]):not([type=radio]), .form select, .form textarea {
    @apply block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30;
  }
  .form .errorlist { @apply mt-1 text-sm text-red-600; }
  .form .helptext { @apply mt-1 block text-xs text-slate-500; }

  .section-title { @apply mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-500; }
  .kpi { @apply relative flex min-h-36 flex-col gap-1 rounded-2xl border p-4 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:shadow-md; background: var(--t50); border-color: var(--t100); }
  .kpi-head { @apply flex items-start justify-between gap-3; }
  .kpi-label { @apply text-xs font-bold uppercase tracking-wide; color: var(--t800); }
  .kpi-icon { @apply grid h-10 w-10 shrink-0 place-items-center rounded-xl text-xl; background: var(--t100); color: var(--t800); }
  .kpi-value { @apply text-3xl font-extrabold leading-tight tabular-nums; color: var(--t800); }
  .kpi-sub { @apply text-xs leading-snug text-slate-600; }
  .kpi-link { @apply mt-auto inline-flex items-center gap-1 pt-2 text-sm font-semibold hover:underline; color: var(--t600); }
  .kpi-soon { @apply border-dashed shadow-none hover:translate-y-0 hover:shadow-none; }
  .kpi-soon .kpi-value { @apply text-xl font-bold; }
  .chip { @apply inline-flex items-center gap-1 rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-50; }
  .chip-active { @apply border-brand-600 bg-brand-50 text-brand-700; }
  .status-badge { @apply inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-semibold; }
  .st-baik { @apply bg-green-50 text-green-800; }
  .st-perhatian { @apply bg-amber-50 text-amber-800; }
  .st-serius { @apply bg-orange-50 text-orange-800; }
  .st-kritis { @apply bg-red-50 text-red-800; }
  .st-netral { @apply bg-slate-100 text-slate-600; }
  .table-wrap { @apply overflow-x-auto rounded-xl border border-slate-200 bg-white; }
  .data-table { @apply min-w-full divide-y divide-slate-200 text-sm; }
  .data-table th { @apply bg-slate-50 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide whitespace-nowrap text-slate-500; }
  .data-table td { @apply px-3 py-2 whitespace-nowrap text-slate-700; }
  .data-table td.num, .data-table th.num { @apply text-right tabular-nums; }
}

@media (prefers-reduced-motion: reduce) {
  .kpi, .kpi:hover { transition: none; transform: none; }
}
```

- [ ] **Step 4: Filter templat, palet, komponen**

Tambahkan ke `dashboards/calc/base.py` di bawah `SEMUA = "Semua"`:
```python
CHART_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]   # urutan tetap
```

`dashboards/templatetags/__init__.py`: kosong.

`dashboards/templatetags/spi.py`:
```python
"""Format angka Indonesia dan warna status untuk templat dasbor."""
from django import template

from dashboards.calc.base import fixed, fold

register = template.Library()

TONE = {"aktif": "baik", "baru": "baik", "rejoin": "baik", "active": "baik", "sudah ada pembayaran": "baik",
        "cuti": "perhatian", "on leave": "perhatian", "belum ada pembayaran": "perhatian", "perlu keputusan": "perhatian",
        "pending": "serius", "off": "kritis"}
IKON = {"baik": "circle-check", "perhatian": "alert-circle", "serius": "alert-triangle", "kritis": "circle-x", "netral": "point"}


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


@register.filter
def angka(v):
    if v is None:
        return ""
    return fixed(v) if _is_number(v) else str(v)


@register.filter
def rp(v):
    if v is None:
        return "—"
    return f"Rp {fixed(v)}" if _is_number(v) else str(v)


@register.filter
def tone_status(status):
    return TONE.get(fold(status), "netral")


@register.filter
def ikon_status(status):
    return IKON[tone_status(status)]
```

`templates/components/kpi_card.html`:
```django
{% comment %}Kartu KPI gaya B. tone: murid|spp|off|kelas|kritis|akad; soon=True -> "menyusul". hx (opsional) = URL HTMX untuk saringan daftar.{% endcomment %}
<div class="kpi {% if soon %}tone-soon kpi-soon{% else %}tone-{{ tone }}{% endif %}">
  <div class="kpi-head">
    <p class="kpi-label">{{ label }}</p>
    <span class="kpi-icon"><i class="ti ti-{{ icon }}" aria-hidden="true"></i></span>
  </div>
  {% if soon %}
    <p class="kpi-value">menyusul</p>
    <p class="kpi-sub">{{ sub|default:"dibangun di tahap berikutnya" }}</p>
  {% else %}
    <p class="kpi-value">{{ value }}</p>
    {% if sub %}<p class="kpi-sub">{{ sub }}</p>{% endif %}
    {% if hx %}<a href="{{ hx }}" hx-get="{{ hx }}" hx-target="#laporan-body" hx-push-url="true" class="kpi-link">{{ link_text|default:"Lihat daftar" }} <i class="ti ti-chevron-right" aria-hidden="true"></i></a>
    {% elif href %}<a href="{{ href }}" class="kpi-link">{{ link_text|default:"Buka" }} <i class="ti ti-chevron-right" aria-hidden="true"></i></a>{% endif %}
  {% endif %}
</div>
```

`templates/components/status_badge.html`:
```django
{% load spi %}{% if status %}<span class="status-badge st-{{ status|tone_status }}"><i class="ti ti-{{ status|ikon_status }}" aria-hidden="true"></i>{{ status }}</span>{% endif %}
```

`templates/components/chart_card.html`:
```django
{% load spi %}
<div class="card flex flex-col p-4" x-data="{ tabel: false }">
  <div class="flex items-start justify-between gap-2">
    <div>
      <h3 class="text-sm font-bold text-slate-800">{{ chart.title }}</h3>
      {% if chart.note %}<p class="text-xs text-slate-500">{{ chart.note }}</p>{% endif %}
    </div>
    <button type="button" class="chip" @click="tabel = !tabel" :aria-pressed="tabel.toString()">
      <i class="ti" :class="tabel ? 'ti-chart-bar' : 'ti-table'" aria-hidden="true"></i><span x-text="tabel ? 'grafik' : 'tabel'">tabel</span></button>
  </div>
  {% if chart.series|length > 1 %}
    <ul class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600">
      {% for s in chart.series %}<li class="flex items-center gap-1.5"><span class="inline-block h-2.5 w-2.5 rounded-sm" style="background: {{ s.color }}"></span>{{ s.label }}</li>{% endfor %}
    </ul>
  {% endif %}
  <div x-show="!tabel" class="relative mt-3 {{ chart.height|default:'h-64' }}">
    <canvas data-chart="{{ chart.id }}" role="img" aria-label="{{ chart.title }}"></canvas>
  </div>
  <div x-show="tabel" x-cloak class="mt-3 max-h-72 overflow-auto">
    <table class="data-table">
      <thead><tr><th></th>{% for s in chart.series %}<th class="num">{{ s.label }}</th>{% endfor %}</tr></thead>
      <tbody>
        {% for row in chart.rows %}
          <tr>
            <td>{% if row.link %}<a href="{{ row.link }}" hx-get="{{ row.link }}" hx-target="#laporan-body" hx-push-url="true" data-chart-link="{{ chart.id }}" data-i="{{ forloop.counter0 }}" class="font-semibold text-brand-600 hover:underline">{{ row.label }}</a>{% else %}{{ row.label }}{% endif %}</td>
            {% for v in row.values %}<td class="num">{% if chart.money %}{{ v|rp }}{% else %}{{ v|angka }}{% endif %}</td>{% endfor %}
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {{ chart|json_script:chart.id }}
</div>
```

Tambahkan ke `dashboards/calc/base.py` pembuat kartu grafik (semua halaman memakainya):
```python


def chart(id, title, labels, series, *, type="bar", horizontal=False, stacked=False, money=False, links=None, note="", height=""):
    """Kartu grafik: series = [(label, data)]; warna kategori diberikan berurutan (tidak pernah diulang)."""
    if len(series) > len(CHART_COLORS):
        raise ValueError("lebih dari 8 seri - gabungkan ke 'Lainnya' atau pecah grafiknya")
    links = links or [None] * len(labels)
    s = [{"label": lab, "data": data, "color": CHART_COLORS[i]} for i, (lab, data) in enumerate(series)]
    return {"id": id, "title": title, "type": type, "labels": labels, "series": s, "horizontal": horizontal, "stacked": stacked,
            "money": money, "links": links, "note": note, "height": height,
            "rows": [{"label": lab, "link": links[i], "values": [x["data"][i] for x in s]} for i, lab in enumerate(labels)]}
```
- [ ] **Step 5: Grafik (Chart.js) dan tata letak dasar**

`static/js/dashboards.js`:
```js
/* Grafik dasbor SPI: membaca spesifikasi JSON dari templat (components/chart_card.html) dan menggambar dengan Chart.js.
   Batang tipis berujung bulat 4px, garis 2px, grid samar, tooltip angka Indonesia; klik batang = tautan saringan di tabel. */
(function () {
  const fmt = new Intl.NumberFormat("id-ID");
  const ink = "#475569", grid = "#e2e8f0";
  const charts = new WeakMap();

  function config(spec) {
    const money = (v) => (spec.money ? "Rp " : "") + fmt.format(v);
    const line = spec.type === "line";
    const datasets = spec.series.map((s) => ({
      label: s.label, data: s.data, borderColor: s.color, backgroundColor: line ? s.color : s.color,
      borderWidth: line ? 2 : 0, borderRadius: line ? 0 : 4, borderSkipped: line ? undefined : "start",
      maxBarThickness: 28, pointRadius: line ? 2 : 0, pointHoverRadius: 5, tension: 0.25,
    }));
    const valueAxis = { beginAtZero: true, stacked: spec.stacked, grid: { color: grid }, border: { display: false },
                        ticks: { color: ink, callback: (v) => (spec.money ? fmt.format(v / 1e6) + " jt" : fmt.format(v)) } };
    const catAxis = { stacked: spec.stacked, grid: { display: false }, ticks: { color: ink, autoSkip: true, maxRotation: 0 } };
    return {
      type: line ? "line" : "bar",
      data: { labels: spec.labels, datasets },
      options: {
        responsive: true, maintainAspectRatio: false, indexAxis: spec.horizontal ? "y" : "x",
        animation: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? false : { duration: 200 },
        interaction: line ? { mode: "index", intersect: false } : { mode: "nearest", intersect: true },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${money(c.parsed[spec.horizontal ? "x" : "y"])}` } },
        },
        scales: spec.horizontal ? { x: valueAxis, y: catAxis } : { x: catAxis, y: valueAxis },
        onHover: (e, els) => { e.native.target.style.cursor = els.length && spec.links && spec.links[els[0].index] ? "pointer" : "default"; },
        onClick: (e, els) => {
          if (!els.length || !spec.links || !spec.links[els[0].index]) return;
          const a = document.querySelector(`[data-chart-link="${spec.id}"][data-i="${els[0].index}"]`);
          if (a) a.click();
        },
      },
    };
  }

  function init(root) {
    if (!window.Chart) return;
    Chart.defaults.font.family = '"Plus Jakarta Sans", ui-sans-serif, system-ui, sans-serif';
    (root || document).querySelectorAll("canvas[data-chart]").forEach((canvas) => {
      const el = document.getElementById(canvas.dataset.chart);
      if (!el) return;
      if (charts.has(canvas)) charts.get(canvas).destroy();
      charts.set(canvas, new Chart(canvas, config(JSON.parse(el.textContent))));
    });
  }

  window.SPICharts = { init };
  document.addEventListener("DOMContentLoaded", () => init(document));
  document.addEventListener("htmx:afterSettle", (e) => init(e.detail.target));
})();
```

`templates/base.html` — di `<head>` setelah baris `app.css` tambahkan:
```django
  <link rel="stylesheet" href="{% static 'vendor/tabler/tabler-icons.min.css' %}">
  <script src="{% static 'vendor/chart.umd.min.js' %}" defer></script>
  <script src="{% static 'js/dashboards.js' %}" defer></script>
```
dan pada menu samping ganti `{% include "core/_icon.html" with name=item.icon %}` dengan `<i class="ti ti-{{ item.icon }} text-xl" aria-hidden="true"></i>`; tombol menu ganti include ikonnya dengan `<i class="ti ti-menu-2 text-xl" aria-hidden="true"></i>`. Ubah `<html lang="id" class="h-full bg-slate-50">` tetap; `<body class="h-full text-slate-800 antialiased" ...>`.

`templates/base_auth.html` — setelah baris `app.css` tambahkan `<link rel="stylesheet" href="{% static 'vendor/tabler/tabler-icons.min.css' %}">`.

`core/nav.py` — ganti `NAV` dengan (ikon Tabler; "Laporan" tampil setelah Task 9 mendaftarkan URL-nya):
```python
NAV = (
    (None, (("Beranda", "core:home", Cap.VIEW, "home"),
            ("Laporan Murid & SPP", "dashboards:laporan", Cap.VIEW, "chart-bar"))),
    ("Admin", (("Impor Data", "importer:upload", Cap.BRANCH_ADMIN, "upload"),
               ("Pengguna & Akses", "accounts:users", Cap.BRANCH_ADMIN, "users"),
               ("Cabang", "branches:list", Cap.MANAGE_ALL, "building"))),
)
```

- [ ] **Step 6: Bangun CSS, validasi palet, jalankan uji**

Run:
```bash
npm run build:css
node "C:/Users/SPIWOR~1/AppData/Local/Temp/claude/bundled-skills/2.1.281/62389971381c8187ab3a330e58b4c942/dataviz/scripts/validate_palette.js" "#2a78d6,#eb6834,#1baf7a,#eda100,#e87ba4,#008300,#6250d6,#e34948" --mode light
.venv/Scripts/python -m pytest
```
Expected: CSS terbangun tanpa error; validator palet tanpa FAIL (WARN kontras = wajib label/tabel — dipenuhi oleh tabel "lihat tabel" dan legenda HTML); semua uji cepat lulus (termasuk `core/tests/test_design.py` 4 passed dan uji menu lama).

- [ ] **Step 7: Commit**

```bash
git add package.json package-lock.json assets static templates core dashboards
git commit -m "feat: sistem desain gaya B - token warna topik, Plus Jakarta Sans, Tabler Icons, kartu KPI & grafik Chart.js lokal" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 8: Halaman Beranda (HOME) + cari murid

**Files:**
- Create: `dashboards/urls.py`, `dashboards/views.py`, `dashboards/pages.py`
- Create: `dashboards/templates/dashboards/beranda.html`, `dashboards/templates/dashboards/_cari_hasil.html`
- Create: `dashboards/tests/test_beranda_view.py`
- Modify: `spi_web/urls.py`, `core/views.py`

**Interfaces:**
- Consumes: `BranchData` (Task 3), `beranda`, `cari_murid` (Task 6), `label` (Task 3), komponen & filter `spi` (Task 7), `require_cap`, `Cap` (1A).
- Produces: URL `dashboards:cari` (`/cari-murid/?q=`), `dashboards.pages.branch_data(request) -> BranchData`, `dashboards.pages.beranda_context(request) -> dict`; `core:home` merender `dashboards/beranda.html`. Task 9 menambah `dashboards:laporan` ke `dashboards/urls.py`.

- [ ] **Step 1: Uji yang gagal**

`dashboards/tests/test_beranda_view.py`:
```python
import pytest
from django.urls import reverse

from dashboards.tests.helpers import make_rows
from students.models import StudentMaster


@pytest.fixture
def murid(branch, other_branch):
    make_rows(StudentMaster, branch, {"std": "STD-000001", "nama": "Ani Wijaya", "st_base": "ACTIVE", "kode_read": "P01"},
              {"std": "STD-000002", "nama": "Budi", "st_base": "ON LEAVE"})
    make_rows(StudentMaster, other_branch, {"std": "STD-000001", "nama": "Wira Cabang Lain", "st_base": "ACTIVE"})


@pytest.mark.django_db
def test_home_shows_colored_cards_with_excel_texts(client, branch, make_user, murid):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    body = client.get("/").content.decode()
    assert "Murid aktif (sekarang)" in body and "tone-murid" in body and "tone-spp" in body and "tone-kelas" in body
    assert "cuti 1  ·  pending 0  ·  status v4 (INPUT CENTER)" in body
    assert body.count("kpi-soon") == 3 and "buku kas belum ada" in body
    assert reverse("dashboards:cari") in body


@pytest.mark.django_db
def test_home_works_for_a_branch_without_data(client, other_branch, make_user):
    client.force_login(make_user("admin.as@spi.test", role="BRANCH_ADMIN", branch=other_branch))
    response = client.get("/")
    assert response.status_code == 200 and "riwayat DB Murid —" in response.content.decode()


@pytest.mark.django_db
def test_search_finds_students_of_the_active_branch_only(client, branch, make_user, murid):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    body = client.get(reverse("dashboards:cari"), {"q": "wi"}).content.decode()
    assert "Ani Wijaya" in body and "P01" in body and "Wira Cabang Lain" not in body and "<html" not in body
    empty = client.get(reverse("dashboards:cari"), {"q": "<script>x"}).content.decode()
    assert "<script>" not in empty and "Tidak ada murid" in empty


@pytest.mark.django_db
def test_search_is_closed_to_teachers_and_guests(client, branch, make_user):
    assert client.get(reverse("dashboards:cari"), {"q": "a"}).status_code == 302
    client.force_login(make_user("guru@spi.test", role="TEACHER", branch=branch, teacher_name="Mr. Uji"))
    assert client.get(reverse("dashboards:cari"), {"q": "a"}).status_code == 403
```

Run: `.venv/Scripts/python -m pytest dashboards/tests/test_beranda_view.py`
Expected: FAIL (`NoReverseMatch: 'dashboards' is not a registered namespace`).

- [ ] **Step 2: URL, tampilan, konteks**

`dashboards/urls.py`:
```python
from django.urls import path

from . import views

app_name = "dashboards"
urlpatterns = [
    path("cari-murid/", views.cari, name="cari"),
]
```

`spi_web/urls.py` — tambahkan `path("", include("dashboards.urls")),` tepat setelah `path("", include("core.urls")),`.

`dashboards/pages.py`:
```python
"""Merakit konteks halaman dasbor dari paket calc (hanya data cabang aktif permintaan ini)."""
from django.utils import timezone

from .calc.base import BranchData, label
from .calc.beranda import beranda


def branch_data(request):
    return BranchData(request.branch, timezone.localdate())


def beranda_context(request):
    h = beranda(branch_data(request))
    spp_label = f"SPP diterima {label(h['spp_bulan'])} (Rp)" if h["spp_bulan"] else "SPP diterima (Rp)"
    return {"h": h, "spp_label": spp_label}
```

`dashboards/views.py`:
```python
from django.shortcuts import render

from core.capabilities import Cap
from core.decorators import require_cap

from .calc.beranda import cari_murid
from .pages import branch_data


@require_cap(Cap.VIEW)
def cari(request):
    q = request.GET.get("q", "")[:60]
    return render(request, "dashboards/_cari_hasil.html", {"rows": cari_murid(branch_data(request), q), "q": q.strip()})
```

`core/views.py` — hapus `from django.apps import apps` dan tuple `COUNT_TABLES`; tambahkan `from dashboards.pages import beranda_context`; ganti dua baris terakhir `home` dengan:
```python
    return render(request, "dashboards/beranda.html", beranda_context(request))
```

- [ ] **Step 3: Templat**

`dashboards/templates/dashboards/beranda.html`:
```django
{% extends "base.html" %}{% load spi %}
{% block title %}Beranda{% endblock %}
{% block content %}
{% url 'dashboards:laporan' as laporan_url %}
<section class="mb-8 overflow-hidden rounded-2xl bg-gradient-to-br from-brand-900 via-brand-700 to-brand-500 p-6 text-white shadow-sm">
  <p class="text-sm font-medium text-blue-100">{{ current_branch.code }}{% if current_branch.city %} · {{ current_branch.city }}{% endif %}</p>
  <h1 class="mt-1 text-2xl font-extrabold sm:text-3xl">{{ current_branch.name }}</h1>
  <p class="mt-2 text-sm text-blue-100">{{ h.judul }}</p>
</section>

<h2 class="section-title"><i class="ti ti-activity" aria-hidden="true"></i>Situasi sekarang</h2>
<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
  {% include "components/kpi_card.html" with tone="murid" icon="users" label="Murid aktif (sekarang)" value=h.aktif|angka sub=h.sub_aktif href=laporan_url link_text="Lihat laporan murid" %}
  {% include "components/kpi_card.html" with tone="spp" icon="cash" label=spp_label value=h.spp|rp sub=h.sub_spp href=laporan_url link_text="Lihat SPP" %}
  {% include "components/kpi_card.html" with tone="off" icon="user-off" label="Murid OFF" value=h.off|angka sub=h.sub_off %}
  {% include "components/kpi_card.html" with tone="kelas" icon="school" label="Kelas aktif" value=h.kelas|angka sub=h.sub_kelas %}
  {% include "components/kpi_card.html" with icon="list-check" label="Perlu tindakan" soon=True sub="mendesak · hari ini · minggu ini — dibangun bersama halaman Tindakan" %}
  {% include "components/kpi_card.html" with tone="kritis" icon="alert-triangle" label="Masalah kritis" value=h.kritis|angka sub=h.sub_kritis %}
  {% include "components/kpi_card.html" with icon="file-invoice" label="Tagihan belum dibayar (Rp)" soon=True sub="tagihan SPP v4 dibuat tombol BULAN BARU (tahap SPP)" %}
  {% include "components/kpi_card.html" with tone="akad" icon="receipt" label="Menunggu verifikasi" value=h.bukti|angka sub=h.sub_bukti %}
  {% include "components/kpi_card.html" with icon="calendar-pause" label="Cuti perlu review · sesi belum dikonfirmasi" soon=True sub="dibangun bersama Input Center & sesi" %}
</div>

<div class="mt-8 grid gap-4 lg:grid-cols-3">
  <section class="card p-5 lg:col-span-2">
    <h2 class="section-title"><i class="ti ti-calendar-event" aria-hidden="true"></i>Operasional bulan ini</h2>
    <p class="text-sm text-slate-700">Periode berjalan (OPEN): <strong>{{ h.periode }}</strong></p>
    <div class="mt-3 flex flex-wrap gap-2">
      <span class="chip"><i class="ti ti-calendar-plus" aria-hidden="true"></i>BULAN BARU · tahap 2</span>
      <span class="chip"><i class="ti ti-lock" aria-hidden="true"></i>TUTUP BULAN · tahap 2</span>
    </div>
  </section>
  <section class="card p-5">
    <h2 class="section-title"><i class="ti ti-clock" aria-hidden="true"></i>Terakhir diperbarui</h2>
    {% if h.impor %}
      <p class="text-sm font-semibold text-slate-800">{{ h.impor.date }}</p>
      <p class="mt-1 break-words text-xs text-slate-500">{{ h.impor.batch }} · {{ h.impor.file }}</p>
    {% else %}<p class="text-sm text-slate-500">Belum ada impor.</p>{% endif %}
  </section>
</div>

<section class="card mt-8 p-5">
  <h2 class="section-title"><i class="ti ti-search" aria-hidden="true"></i>Cari murid</h2>
  <input type="search" name="q" placeholder="Ketik sebagian nama…" autocomplete="off" aria-label="Cari murid"
         class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
         hx-get="{% url 'dashboards:cari' %}" hx-trigger="input changed delay:300ms, search" hx-target="#cari-hasil">
  <div id="cari-hasil" class="mt-3" aria-live="polite"><p class="text-sm text-slate-500">Ketik nama di kotak di atas.</p></div>
</section>

<section class="mt-8">
  <h2 class="section-title"><i class="ti ti-layout-grid" aria-hidden="true"></i>Menu</h2>
  <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
    {% for group in nav %}{% for item in group.items %}{% if item.href != "/" %}
      <a href="{{ item.href }}" class="card flex items-center gap-3 p-4 transition hover:border-brand-500 hover:shadow-md">
        <span class="grid h-10 w-10 place-items-center rounded-xl bg-brand-50 text-xl text-brand-700"><i class="ti ti-{{ item.icon }}" aria-hidden="true"></i></span>
        <span class="font-semibold text-slate-800">{{ item.label }}</span></a>
    {% endif %}{% endfor %}{% endfor %}
  </div>
</section>
{% endblock %}
```

`dashboards/templates/dashboards/_cari_hasil.html`:
```django
{% if not q %}<p class="text-sm text-slate-500">Ketik nama di kotak di atas.</p>
{% elif not rows %}<p class="text-sm text-slate-500">Tidak ada murid dengan nama “{{ q }}”.</p>
{% else %}
<div class="table-wrap">
  <table class="data-table">
    <thead><tr><th>Nama murid</th><th>Status sekarang</th><th>Kode kelas</th><th>Guru</th><th>Student ID</th></tr></thead>
    <tbody>
      {% for r in rows %}
        <tr><td class="font-semibold text-slate-900">{{ r.nama }}</td><td>{% include "components/status_badge.html" with status=r.status %}</td>
          <td>{{ r.kode|default:"—" }}</td><td>{{ r.guru|default:"—" }}</td><td class="tabular-nums">{{ r.std }}</td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% if rows|length == 20 %}<p class="mt-2 text-xs text-slate-500">Menampilkan 20 nama pertama — ketik lebih lengkap untuk mempersempit.</p>{% endif %}
{% endif %}
```

Catatan: `{% url 'dashboards:laporan' as laporan_url %}` tidak gagal walau URL belum ada (bentuk `as` menghasilkan kosong), jadi Beranda berfungsi sebelum Task 9.

- [ ] **Step 4: Jalankan uji**

Run:
```bash
npm run build:css
.venv/Scripts/python -m pytest
```
Expected: semua uji cepat lulus (termasuk `test_beranda_view.py` 4 passed dan uji lama `core/tests/test_shell.py`).

- [ ] **Step 5: Commit**

```bash
git add dashboards core spi_web static/css
git commit -m "feat: Beranda - kartu situasi berwarna sama dengan HOME Excel, cari murid sambil mengetik" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 9: Halaman Laporan Murid & SPP (DASHBOARD)

**Files:**
- Modify: `dashboards/urls.py`, `dashboards/views.py`, `dashboards/pages.py`
- Create: `dashboards/templates/dashboards/laporan.html`, `dashboards/templates/dashboards/_laporan_body.html`
- Create: `dashboards/tests/test_laporan_view.py`
- Modify: `core/tests/test_layout.py` (halaman Laporan ikut uji tabel bergulir)

**Interfaces:**
- Consumes: `Filter`, `ringkasan_murid`, `baris_laporan` (Task 4); `ringkasan_spp`, `bulanan` (Task 5); `periode_v4`, `periode_default` (Task 6); `chart`, `HIST_MONTHS`, `HIST_END`, `PERIOD_MONTHS`, `period_code`, `parse_period`, `label`, `short_label`, `fold`, `SEMUA` (Task 3/7); `angka`, `rp` (Task 7); `branch_data` (Task 8).
- Produces: URL `dashboards:laporan` (`/laporan/`, parameter GET `bulan=yyyy-mm`, `program`, `tipe`, `mode`, `guru`, `daftar`, `periode=yyyy-mm`); `dashboards.pages.parse_params(data, params) -> (Filter, daftar, periode)`, `laporan_context(request) -> dict` (kunci `f`, `opsi`, `filter_label`, `murid_cards`, `spp_cards`, `charts`, `perhatian`, `daftar`, `v4`, `kosong`).

- [ ] **Step 1: Uji yang gagal**

`dashboards/tests/test_laporan_view.py`:
```python
import datetime

import pytest
from django.urls import reverse

from branches.models import BranchSetting
from dashboards.tests.helpers import make_rows
from finance.models import BukuKas
from students.models import DBulan, DMurid, StudentMaster

D = datetime.date
URL = "/laporan/"


@pytest.fixture
def data(branch, other_branch):
    murid = [{"v1": f"M{i:02d}", "nama": f"Murid {i:02d}", "std": f"STD-0000{i:02d}"} for i in range(1, 36)]
    make_rows(DMurid, branch, *murid)
    make_rows(StudentMaster, branch, *[{"std": m["std"], "nama": m["nama"], "st_base": "ACTIVE"} for m in murid])
    rows = []
    for i in range(1, 36):
        rows.append({"key": f"M{i:02d}|202608", "v1": f"M{i:02d}", "bulan": D(2026, 8, 1), "status": "Aktif", "grade": "Foundation 1.0",
                     "guru": "Ms. Linda", "guru_asli": "Linda", "tipe": "Partner", "mode": "Onsite"})
        rows.append({"key": f"M{i:02d}|202609", "v1": f"M{i:02d}", "bulan": D(2026, 9, 1), "status": "Off" if i <= 2 else "Aktif",
                     "grade": "Foundation 1.0", "guru": "Ms. Linda", "guru_asli": "Linda", "tipe": "Partner", "mode": "Onsite"})
    make_rows(DBulan, branch, *rows)
    make_rows(BukuKas, branch, {"bulan": D(2026, 9, 1), "tgl": D(2026, 9, 5), "jenis": "SPP", "nominal": 500000, "dihitung": "YA",
                                "ss1": "STD-000003", "sb1": 500000, "lid": "BK-1"})
    make_rows(DMurid, other_branch, {"v1": "X1", "nama": "Rahasia Cabang Lain", "std": "STD-000001"})


def get(client, **params):
    return client.get(URL, params)


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["CSO", "FINANCE", "ACADEMIC", "MANAGER", "BRANCH_ADMIN"])
def test_view_roles_see_the_report(client, branch, make_user, data, role):
    client.force_login(make_user(f"{role.lower()}@spi.test", role=role, branch=branch))
    response = get(client)
    body = response.content.decode()
    assert response.status_code == 200 and "Laporan Murid &amp; SPP" in body and "Rahasia Cabang Lain" not in body
    ctx = response.context
    assert ctx["f"].bulan == D(2026, 9, 1) and [c["value"] for c in ctx["murid_cards"][:2]] == ["33", "33"]
    assert ctx["spp_cards"][0]["value"] == "Rp 500.000" and ctx["spp_cards"][3]["value"] == "1  ·  3%"
    assert len(ctx["charts"]) == 7 and "Laporan Murid &amp; SPP" in body


@pytest.mark.django_db
def test_teacher_and_guest_cannot_open_it(client, branch, make_user):
    assert get(client).status_code == 302
    client.force_login(make_user("guru@spi.test", role="TEACHER", branch=branch, teacher_name="Mr. Uji"))
    assert get(client).status_code == 403


@pytest.mark.django_db
def test_htmx_gets_the_body_only_and_history_restore_gets_the_page(client, branch, make_user, data):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    part = client.get(URL, {"bulan": "2026-08"}, HTTP_HX_REQUEST="true")
    assert part.status_code == 200 and "<html" not in part.content.decode() and 'id="laporan-filter"' in part.content.decode()
    assert "HX-Request" in part["Vary"]
    full = client.get(URL, HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
    assert "<html" in full.content.decode()


@pytest.mark.django_db
def test_invalid_parameters_fall_back_to_defaults(client, branch, make_user, data):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    response = get(client, bulan="xx", program="Robotik", guru="<script>alert(1)</script>", daftar="apa", periode="2099-01")
    assert response.status_code == 200
    f = response.context["f"]
    assert (f.bulan, f.program, f.guru, response.context["daftar"]["key"]) == (D(2026, 9, 1), "Semua", "Semua", "")
    assert "<script>alert(1)</script>" not in response.content.decode()
    assert get(client, guru="ms. linda").context["f"].guru == "Ms. Linda"            # tanpa beda huruf -> nilai daftar


@pytest.mark.django_db
def test_student_list_shows_30_then_all_and_filters(client, branch, make_user, data):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    d = get(client).context["daftar"]
    assert (len(d["rows"]), d["total"], d["lebih"]) == (30, 35, True)
    assert len(get(client, daftar="semua").context["daftar"]["rows"]) == 35
    off = get(client, daftar="off-baru").context["daftar"]
    assert [r["nama"] for r in off["rows"]] == ["Murid 01", "Murid 02"] and off["judul"] == "Off baru"
    belum = get(client, daftar="belum-bayar").context["daftar"]
    assert belum["total"] == 32 and "Murid 03" not in [r["nama"] for r in belum["rows"]]


@pytest.mark.django_db
def test_months_before_the_cash_book_show_a_dash(client, branch, make_user, data):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    cards = get(client, bulan="2024-06").context["spp_cards"]
    assert [c["value"] for c in cards[:2]] == ["—", "—"] and cards[3]["value"] == "—" and cards[7]["soon"]


@pytest.mark.django_db
def test_undecided_august_journal_needs_a_decision(client, branch, make_user, data):
    BranchSetting.objects.create(branch=branch, key="jurnal_agu", value_text="BELUM DIPUTUSKAN")
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    ctx = get(client, bulan="2026-08").context
    assert ctx["spp_cards"][3]["value"] == "perlu keputusan" and ctx["spp_cards"][4]["value"] == "perlu keputusan"
    assert ctx["perhatian"][2]["catatan"] == "Agustus 2026: perlu keputusan jurnal (SETTINGS)"


@pytest.mark.django_db
def test_branch_without_data_renders(client, other_branch, make_user):
    StudentMaster.objects.all().delete()
    client.force_login(make_user("admin.as@spi.test", role="BRANCH_ADMIN", branch=other_branch))
    response = get(client)
    assert response.status_code == 200 and response.context["kosong"] and "Belum ada data murid" in response.content.decode()


@pytest.mark.django_db
def test_menu_links_to_the_report(client, branch, make_user):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    assert f'href="{reverse("dashboards:laporan")}"' in client.get("/").content.decode()
```

Penjelasan angka uji: Sep 2026 = 35 murid; M01, M02 Off (Agustus Aktif → Off baru 2); Aktif 33; total = Aktif + Cuti = 33. Kas Sep: 500.000 untuk STD-000003 → sudah bayar 1 dari 33 aktif = 3%; belum bayar 32.

Modify `core/tests/test_layout.py` — tambahkan `reverse("dashboards:laporan")` ke daftar `pages` pada uji tabel bergulir.

Run: `.venv/Scripts/python -m pytest dashboards/tests/test_laporan_view.py`
Expected: FAIL (`NoReverseMatch` / 404 untuk `/laporan/`).

- [ ] **Step 2: Konteks halaman**

Tambahkan ke `dashboards/pages.py` (impor digabung di atas berkas):
```python
from urllib.parse import urlencode

from django.urls import reverse

from .calc.base import HIST_END, HIST_MONTHS, PERIOD_MONTHS, SEMUA, chart, fold, parse_period, period_code, short_label
from .calc.kas import BELUM, KEPUTUSAN, bulanan, ringkasan_spp
from .calc.laporan import STATUS_GRAFIK, Filter, ringkasan_murid
from .calc.operasional import periode_default, periode_v4
from .templatetags.spi import angka, rp

DAFTAR = {"semua": "Semua murid (sesuai filter)", "aktif": "Murid aktif", "status-aktif": "Status Aktif", "baru": "Murid baru",
          "rejoin": "Rejoin", "cuti": "Cuti", "off": "Off", "off-baru": "Off baru", "belum-bayar": "Aktif belum ada pembayaran"}
STATUS_KEY = {"Aktif": "status-aktif", "Baru": "baru", "Rejoin": "rejoin", "Cuti": "cuti", "Off": "off"}
TAMPIL = 30
PERHATIAN = 8


def _pick(value, options):
    v = fold(value)
    return next((o for o in options if fold(o) == v), SEMUA)


def parse_params(data, params):
    months = {period_code(m): m for m in HIST_MONTHS}
    f = Filter(months.get(params.get("bulan", ""), HIST_END), _pick(params.get("program"), data.programs),
               _pick(params.get("tipe"), data.tipes), _pick(params.get("mode"), data.modes), _pick(params.get("guru"), data.gurus))
    daftar = params.get("daftar", "")
    per = parse_period(params.get("periode", ""))
    if per not in PERIOD_MONTHS:
        per = periode_default(data)
        per = per if per in PERIOD_MONTHS else HIST_END
    return f, (daftar if daftar in DAFTAR else ""), per


def _url(f, per, daftar=""):
    q = {"bulan": period_code(f.bulan)}
    q.update({k: v for k, v in (("program", f.program), ("tipe", f.tipe), ("mode", f.mode), ("guru", f.guru)) if v != SEMUA})
    q["periode"] = period_code(per)
    if daftar:
        q["daftar"] = daftar
    return f"{reverse('dashboards:laporan')}?{urlencode(q)}"


def _cocok(key, b, per_baris):
    if key in ("", "semua"):
        return True
    if key == "aktif":
        return b.kelompok == "Aktif"
    if key == "status-aktif":
        return fold(b.status) == "aktif"
    if key in ("baru", "rejoin"):
        return fold(b.status) == key
    if key in ("cuti", "off"):
        return fold(b.kelompok) == key
    if key == "off-baru":
        return b.off_baru
    return per_baris[id(b.murid)][1] == BELUM                         # belum-bayar


def _card(tone, icon, label, value, sub, hx=None, soon=False):
    return {"tone": tone, "icon": icon, "label": label, "value": value, "sub": sub, "hx": hx, "soon": soon}


def _perhatian(judul, ikon, rows, kolom, url, catatan=""):
    n = len(rows)
    teks = catatan or (f"menampilkan {PERHATIAN} dari {n}" if n > PERHATIAN else f"total: {n}")
    return {"judul": judul, "ikon": ikon, "rows": [[getattr(b, k) or "—" for k in kolom] for b in rows[:PERHATIAN]], "catatan": teks,
            "url": url if n else None}


def laporan_context(request):
    data = branch_data(request)
    f, daftar_key, per = parse_params(data, request.GET)
    m, s = ringkasan_murid(data, f), ringkasan_spp(data, f)
    u = lambda key="": _url(f, per, key)  # noqa: E731
    murid_cards = [
        _card("murid", "users", "Total data murid", angka(m["murid"][0]), "Aktif + Cuti (tanpa Off)", u("semua")),
        _card("murid", "user-check", "Murid aktif", angka(m["murid"][1]), "Aktif + Baru + Rejoin", u("aktif")),
        _card("akad", "user-plus", "Murid baru", angka(m["murid"][2]), "status 'Baru' bulan ini", u("baru")),
        _card("kelas", "arrow-back-up", "Rejoin", angka(m["murid"][3]), "kembali dari cuti/off", u("rejoin")),
        _card("off", "player-pause", "Cuti", angka(m["murid"][4]), "status 'Cuti' bulan ini", u("cuti")),
        _card("kritis", "user-off", "Off (status bulan ini)", angka(m["murid"][5]), "seluruh murid berstatus Off", u("off")),
        _card("kritis", "user-minus", "Off baru", angka(m["murid"][6]), "baru Off dibanding bulan lalu", u("off-baru")),
        _card("soon", "chart-line", "Retensi", "TIDAK TERSEDIA", "belum ada definisi retensi di data sumber (lihat PANDUAN)"),
    ]
    v = s["spp"]
    spp_cards = [
        _card("spp", "cash", "SPP diterima (Rp)", rp(v[0]), "buku kas bulan terpilih · semua murid"),
        _card("spp", "calendar-dollar", "SPP tahun ini s/d bulan ini (Rp)", rp(v[1]), "Januari sampai bulan terpilih"),
        _card("murid", "users", "Murid aktif", angka(v[2]), "sesuai filter", u("aktif")),
        _card("spp", "circle-check", "Aktif sudah bayar", angka(v[3]), "ada penerimaan di buku kas"),
        _card("off", "hourglass", "Aktif belum ada pembayaran", angka(v[4]), "bukan tunggakan: belum tercatat di buku kas",
              u("belum-bayar") if isinstance(v[4], int) and v[4] else None),
        _card("kritis", "link-off", "Penerimaan belum tertaut", angka(v[5]), "baris SPP tanpa nama murid jelas"),
        _card("akad", "zoom-question", "Tautan lemah (cek)", angka(v[6]), "semua bulan · mohon dicek di BUKU_KAS"),
        _card("soon", "user-question", "Nama menunggu", "", "butuh data CEK NAMA (menyusul)", soon=True),
    ]
    kas = bulanan(data)
    bayar_note = "belum ada buku kas" if v[3] == "—" else KEPUTUSAN if s["keputusan"] else ""
    sudah = int(str(v[3]).split()[0]) if isinstance(v[3], str) and v[3][:1].isdigit() else 0
    charts = [
        chart("c-tren", "Tren murid 33 bulan", [t[0] for t in m["tren"]],
              [("Aktif", [t[1] for t in m["tren"]]), ("Cuti", [t[2] for t in m["tren"]]), ("Off", [t[3] for t in m["tren"]]),
               ("Baru", [t[4] for t in m["tren"]])], type="line", note="semua murid DB Murid · filter selain bulan"),
        chart("c-status", "Status murid bulan ini", STATUS_GRAFIK, [("Murid", [n for _l, n in m["status"]])],
              links=[u(STATUS_KEY[x]) for x in STATUS_GRAFIK], note="klik batang untuk melihat daftarnya"),
        chart("c-level", "Murid aktif per level", [x[0] for x in m["level"]], [("Murid aktif", [x[1] for x in m["level"]])],
              horizontal=True, height="h-96"),
        chart("c-tipe", "Murid aktif per tipe kelas", [x[0] for x in m["tipe"]], [("Murid aktif", [x[1] for x in m["tipe"]])]),
        chart("c-guru", "Murid aktif per guru (10 teratas)", [x[0] for x in m["guru"]], [("Murid aktif", [x[1] for x in m["guru"]])],
              horizontal=True, height="h-96"),
        chart("c-kas", "SPP diterima per bulan (buku kas)", [short_label(k[0]) for k in kas],
              [("Tertaut ke murid", [k[2] for k in kas]), ("Belum tertaut", [k[3] for k in kas])], stacked=True, money=True,
              note="semua murid · Jenis SPP, Dihitung YA"),
        chart("c-bayar", "Status pembayaran murid aktif", ["Sudah ada pembayaran", "Belum ada pembayaran"],
              [("Murid", [sudah, v[4] if isinstance(v[4], int) else 0])], links=[None, u("belum-bayar")], note=bayar_note),
    ]
    catatan_bayar = "Agustus 2026: perlu keputusan jurnal (SETTINGS)" if s["keputusan"] else ""
    perhatian = [
        _perhatian("Murid baru", "user-plus", m["baru"], ("nama", "level"), u("baru")),
        _perhatian("Off baru", "user-minus", m["off_baru"], ("nama", "level"), u("off-baru")),
        _perhatian("Aktif belum ada pembayaran", "hourglass", s["belum_bayar"], ("nama", "guru", "tipe"), u("belum-bayar"), catatan_bayar),
    ]
    semua = [b for b in m["daftar"] if _cocok(daftar_key, b, s["per_baris"])]
    tampil = semua if daftar_key else semua[:TAMPIL]
    daftar = {"key": daftar_key, "judul": DAFTAR.get(daftar_key, "Daftar murid"), "total": len(semua), "lebih": len(semua) > len(tampil),
              "semua_url": u("semua"), "reset_url": u(),
              "rows": [{"nama": b.nama, "status": b.status, "program": b.program, "level": b.level, "kode": b.kode_kelas, "guru": b.guru,
                        "tipe": b.tipe, "mode": b.mode, "spp": s["per_baris"][id(b.murid)][0], "bayar": s["per_baris"][id(b.murid)][1],
                        "std": b.std} for b in tampil]}
    v4 = periode_v4(data, per)
    label_filter = label(f.bulan) + "".join(f"  ·  {x}" for x in (f.program, f.tipe, f.mode) if x != SEMUA) + \
        (f"  ·  {f.guru}" if f.guru != SEMUA else "  ·  semua guru")
    return {
        "f": f, "filter_label": label_filter, "periode": per, "periode_kode": period_code(per),
        "opsi": {"bulan": [(period_code(x), label(x)) for x in reversed(HIST_MONTHS)], "program": data.programs, "tipe": data.tipes,
                 "mode": data.modes, "guru": data.gurus, "periode": [(period_code(x), label(x)) for x in PERIOD_MONTHS]},
        "bulan_kode": period_code(f.bulan),
        "murid_cards": murid_cards, "spp_cards": spp_cards, "charts": charts, "perhatian": perhatian, "daftar": daftar,
        "v4": {"status": list(zip(["ACTIVE", "ON LEAVE", "OFF", "PENDING"], v4["status"])),
               "aktivitas": list(zip(["Murid masuk", "OFF baru", "Cuti baru", "Aktif kembali", "Sesi terlaksana", "Sesi batal", "Lead baru",
                                      "Follow-up", "Catatan akademik"], v4["aktivitas"]))},
        "kosong": not data.d_murid,
    }
```
`label` sudah diimpor dari `.calc.base` (Task 8); gabungkan daftar impor `.calc.base` menjadi satu baris.

- [ ] **Step 3: Tampilan & URL**

`dashboards/urls.py` — tambahkan `path("laporan/", views.laporan, name="laporan"),` sebagai baris pertama `urlpatterns`.

Tambahkan ke `dashboards/views.py`:
```python
from django.utils.cache import patch_vary_headers

from .pages import laporan_context


@require_cap(Cap.VIEW)
def laporan(request):
    partial = request.headers.get("HX-Request") == "true" and request.headers.get("HX-History-Restore-Request") != "true"
    response = render(request, "dashboards/_laporan_body.html" if partial else "dashboards/laporan.html", laporan_context(request))
    patch_vary_headers(response, ["HX-Request"])
    return response
```

`dashboards/templates/dashboards/laporan.html`:
```django
{% extends "base.html" %}
{% block title %}Laporan Murid & SPP{% endblock %}
{% block content %}
<div class="mb-6">
  <h1 class="text-2xl font-extrabold text-slate-900">Laporan Murid &amp; SPP</h1>
  <p class="text-sm text-slate-500">{{ current_branch.name }} · status bulan terpilih (DB Murid) dan buku kas · angka sama dengan LAPORAN Excel</p>
</div>
<div id="laporan-body">{% include "dashboards/_laporan_body.html" %}</div>
{% endblock %}
```

`dashboards/templates/dashboards/_laporan_body.html`:
```django
{% load spi %}
<form id="laporan-filter" method="get" action="{% url 'dashboards:laporan' %}" hx-get="{% url 'dashboards:laporan' %}"
      hx-target="#laporan-body" hx-push-url="true" hx-trigger="change" hx-indicator="#laporan-loading">
  <div class="card sticky top-16 z-[5] mb-6 p-4">
    <div class="grid gap-3 sm:grid-cols-3 lg:grid-cols-5">
      <label class="text-xs font-semibold uppercase tracking-wide text-slate-500">Bulan
        <select name="bulan" class="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium normal-case tracking-normal text-slate-900">
          {% for code, lab in opsi.bulan %}<option value="{{ code }}" {% if code == bulan_kode %}selected{% endif %}>{{ lab }}</option>{% endfor %}
        </select></label>
      <label class="text-xs font-semibold uppercase tracking-wide text-slate-500">Program
        <select name="program" class="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium normal-case tracking-normal text-slate-900">
          <option value="Semua">Semua</option>
          {% for x in opsi.program %}<option value="{{ x }}" {% if x == f.program %}selected{% endif %}>{{ x }}</option>{% endfor %}
        </select></label>
      <label class="text-xs font-semibold uppercase tracking-wide text-slate-500">Tipe kelas
        <select name="tipe" class="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium normal-case tracking-normal text-slate-900">
          <option value="Semua">Semua</option>
          {% for x in opsi.tipe %}<option value="{{ x }}" {% if x == f.tipe %}selected{% endif %}>{{ x }}</option>{% endfor %}
        </select></label>
      <label class="text-xs font-semibold uppercase tracking-wide text-slate-500">Mode
        <select name="mode" class="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium normal-case tracking-normal text-slate-900">
          <option value="Semua">Semua</option>
          {% for x in opsi.mode %}<option value="{{ x }}" {% if x == f.mode %}selected{% endif %}>{{ x }}</option>{% endfor %}
        </select></label>
      <label class="text-xs font-semibold uppercase tracking-wide text-slate-500">Guru
        <select name="guru" class="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium normal-case tracking-normal text-slate-900">
          <option value="Semua">Semua</option>
          {% for x in opsi.guru %}<option value="{{ x }}" {% if x == f.guru %}selected{% endif %}>{{ x }}</option>{% endfor %}
        </select></label>
    </div>
    <div class="mt-3 flex flex-wrap items-center gap-2 text-sm">
      <span class="chip chip-active"><i class="ti ti-filter" aria-hidden="true"></i>{{ filter_label }}</span>
      <a href="{% url 'dashboards:laporan' %}" hx-get="{% url 'dashboards:laporan' %}" hx-target="#laporan-body" hx-push-url="true" class="chip">Atur ulang</a>
      <span id="laporan-loading" class="htmx-indicator text-xs text-slate-500">memuat…</span>
      <noscript><button class="btn btn-primary">Terapkan</button></noscript>
    </div>
  </div>

  {% if kosong %}
    <div class="card mb-6 border-dashed p-5 text-sm text-slate-600"><i class="ti ti-database-off" aria-hidden="true"></i>
      Belum ada data murid untuk cabang ini — impor workbook di menu Impor Data. Angka di bawah bernilai nol.</div>
  {% endif %}

  <h2 class="section-title"><i class="ti ti-users" aria-hidden="true"></i>Murid <span class="normal-case tracking-normal text-slate-400">· status bulan terpilih; Aktif = Aktif + Baru + Rejoin</span></h2>
  <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
    {% for c in murid_cards %}{% include "components/kpi_card.html" with tone=c.tone icon=c.icon label=c.label value=c.value sub=c.sub hx=c.hx soon=c.soon %}{% endfor %}
  </div>

  <h2 class="section-title mt-8"><i class="ti ti-cash" aria-hidden="true"></i>SPP <span class="normal-case tracking-normal text-slate-400">· buku kas bulan terpilih; total bulan = semua murid</span></h2>
  <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
    {% for c in spp_cards %}{% include "components/kpi_card.html" with tone=c.tone icon=c.icon label=c.label value=c.value sub=c.sub hx=c.hx soon=c.soon %}{% endfor %}
  </div>

  <h2 class="section-title mt-8"><i class="ti ti-chart-histogram" aria-hidden="true"></i>Grafik</h2>
  <div class="grid gap-4 lg:grid-cols-2">
    {% for c in charts %}<div class="{% if forloop.first %}lg:col-span-2{% endif %}">{% include "components/chart_card.html" with chart=c %}</div>{% endfor %}
  </div>

  <h2 class="section-title mt-8"><i class="ti ti-bell" aria-hidden="true"></i>Perlu perhatian</h2>
  <div class="grid gap-4 lg:grid-cols-3">
    {% for p in perhatian %}
      <div class="card p-4">
        <h3 class="flex items-center gap-2 text-sm font-bold text-slate-800"><i class="ti ti-{{ p.ikon }}" aria-hidden="true"></i>{{ p.judul }}</h3>
        <ul class="mt-3 divide-y divide-slate-100 text-sm">
          {% for r in p.rows %}<li class="flex justify-between gap-3 py-1.5"><span class="font-medium text-slate-800">{{ r.0 }}</span><span class="text-right text-xs text-slate-500">{{ r|slice:"1:"|join:" · " }}</span></li>
          {% empty %}<li class="py-1.5 text-slate-500">tidak ada</li>{% endfor %}
        </ul>
        <p class="mt-2 text-xs text-slate-500">{{ p.catatan }}{% if p.url %} · <a href="{{ p.url }}" hx-get="{{ p.url }}" hx-target="#laporan-body" hx-push-url="true" class="font-semibold text-brand-600 hover:underline">lihat daftar</a>{% endif %}</p>
      </div>
    {% endfor %}
  </div>

  <div id="daftar-murid" class="mt-8 flex flex-wrap items-end justify-between gap-2">
    <h2 class="section-title mb-0"><i class="ti ti-list-details" aria-hidden="true"></i>{{ daftar.judul }} <span class="normal-case tracking-normal text-slate-400">· {{ daftar.total }} murid</span></h2>
    {% if daftar.key %}<a href="{{ daftar.reset_url }}" hx-get="{{ daftar.reset_url }}" hx-target="#laporan-body" hx-push-url="true" class="chip"><i class="ti ti-x" aria-hidden="true"></i>hapus saringan</a>{% endif %}
  </div>
  <div class="table-wrap mt-3">
    <table class="data-table">
      <thead><tr><th>Nama</th><th>Status</th><th>Program</th><th>Level</th><th>Kode kelas</th><th>Guru</th><th>Tipe</th><th>Mode</th><th class="num">SPP (Rp)</th><th>Status bayar</th><th>Student ID</th></tr></thead>
      <tbody>
        {% for r in daftar.rows %}
          <tr><td class="font-semibold text-slate-900">{{ r.nama }}</td><td>{% include "components/status_badge.html" with status=r.status %}</td>
            <td>{{ r.program }}</td><td>{{ r.level }}</td><td>{{ r.kode }}</td><td>{{ r.guru }}</td><td>{{ r.tipe }}</td><td>{{ r.mode }}</td>
            <td class="num">{{ r.spp|angka }}</td><td>{% include "components/status_badge.html" with status=r.bayar %}</td><td class="tabular-nums">{{ r.std }}</td></tr>
        {% empty %}<tr><td colspan="11" class="py-6 text-center text-slate-500">Tidak ada murid untuk filter ini.</td></tr>{% endfor %}
      </tbody>
    </table>
  </div>
  {% if daftar.lebih %}<p class="mt-2 text-sm text-slate-600">Menampilkan {{ daftar.rows|length }} dari {{ daftar.total }} murid ·
    <a href="{{ daftar.semua_url }}" hx-get="{{ daftar.semua_url }}" hx-target="#laporan-body" hx-push-url="true" class="font-semibold text-brand-600 hover:underline">tampilkan semua</a></p>{% endif %}

  <div class="mt-8 flex flex-wrap items-end justify-between gap-3">
    <h2 class="section-title mb-0"><i class="ti ti-calendar-stats" aria-hidden="true"></i>Periode operasional v4</h2>
    <label class="text-xs font-semibold uppercase tracking-wide text-slate-500">Periode
      <select name="periode" class="ml-2 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium normal-case tracking-normal text-slate-900">
        {% for code, lab in opsi.periode %}<option value="{{ code }}" {% if code == periode_kode %}selected{% endif %}>{{ lab }}</option>{% endfor %}
      </select></label>
  </div>
  <div class="mt-3 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
    {% for st, n in v4.status %}
      <div class="card flex items-center justify-between p-4">{% include "components/status_badge.html" with status=st %}<span class="text-2xl font-extrabold tabular-nums text-slate-900">{{ n|angka }}</span></div>
    {% endfor %}
  </div>
  <div class="card mt-4 grid gap-x-6 gap-y-2 p-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
    {% for lab, n in v4.aktivitas %}<div class="flex justify-between border-b border-slate-100 py-1"><span class="text-slate-600">{{ lab }}</span><span class="font-bold tabular-nums">{{ n|angka }}</span></div>{% endfor %}
    <div class="flex justify-between border-b border-slate-100 py-1 text-slate-400"><span>Tagihan · terbayar · sisa</span><span>menyusul (tahap SPP)</span></div>
  </div>
</form>
```

- [ ] **Step 4: Jalankan uji**

Run:
```bash
npm run build:css
.venv/Scripts/python -m pytest
```
Expected: semua uji cepat lulus (termasuk `test_laporan_view.py` 13 passed — 5 peran + 8 uji lain — dan `core/tests/test_layout.py` dengan halaman Laporan).

- [ ] **Step 5: Commit**

```bash
git add dashboards core static/css
git commit -m "feat: Laporan Murid & SPP - filter HTMX, kartu KPI, 7 grafik, daftar perhatian & murid, periode v4" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 10: Akun demo per peran

**Files:**
- Modify: `spi_web/settings.py`, `accounts/apps.py`, `accounts/views.py`, `accounts/urls.py`, `accounts/templates/accounts/login.html`
- Create: `accounts/checks.py`, `accounts/demo.py`, `accounts/management/__init__.py`, `accounts/management/commands/__init__.py`, `accounts/management/commands/seed_demo_accounts.py`
- Create: `accounts/tests/test_demo.py`, `docs/AKUN_DEMO.md`

**Interfaces:**
- Consumes: `User`, `Membership`, `Branch`, `TeacherMaster` (1A).
- Produces: settings `DEMO_ACCOUNTS` (bool), `DEMO_PASSWORD` (str), `ENV_FILE` (Path); pemeriksaan sistem `spi.E001`; `accounts.demo.DEMO_USERS`, `demo_enabled()`, `ensure_password(env_file) -> str`, `seed(password) -> list[dict]`, `available()`; perintah `seed_demo_accounts`; URL `accounts:demo_login` (POST `email`).

- [ ] **Step 1: Uji yang gagal**

`accounts/tests/test_demo.py`:
```python
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse

from accounts.checks import demo_accounts_check
from accounts.demo import DEMO_USERS, ensure_password
from branches.models import Membership
from dashboards.tests.helpers import make_rows
from masterdata.models import TeacherMaster


@pytest.fixture
def demo(settings, tmp_path):
    settings.DEBUG = True
    settings.DEMO_ACCOUNTS = True
    settings.DEMO_PASSWORD = ""
    settings.ENV_FILE = tmp_path / ".env"
    settings.ENV_FILE.write_text("SECRET_KEY=x\n", encoding="utf-8")
    return settings


def test_demo_flag_without_debug_is_a_system_error(settings):
    settings.DEBUG, settings.DEMO_ACCOUNTS = False, True
    assert [e.id for e in demo_accounts_check(None)] == ["spi.E001"]
    settings.DEBUG = True
    assert demo_accounts_check(None) == []


def test_password_is_generated_once_into_the_env_file(demo):
    first = ensure_password(demo.ENV_FILE)
    assert len(first) >= 16 and f"DEMO_PASSWORD={first}" in demo.ENV_FILE.read_text(encoding="utf-8")
    assert ensure_password(demo.ENV_FILE) == first


@pytest.mark.django_db
def test_seed_creates_every_role_and_is_idempotent(demo, branch, other_branch, django_user_model):
    make_rows(TeacherMaster, branch, {"tid": "T-01", "name": "Ms. Linda"}, {"tid": "T-02", "name": "Mr. Bram"})
    call_command("seed_demo_accounts")
    call_command("seed_demo_accounts")
    users = django_user_model.objects.filter(email__endswith="@spi.local")
    assert users.count() == len(DEMO_USERS) == 8 and all(u.is_active and u.email_verified_at for u in users)
    assert users.get(email="superadmin@spi.local").is_super_admin
    roles = {(m.user.email, m.branch.code, m.role) for m in Membership.objects.select_related("user", "branch")}
    assert ("cso.jkt@spi.local", "SPI-JKT", "CSO") in roles and ("admin.as@spi.local", "SPI-AS", "BRANCH_ADMIN") in roles
    assert Membership.objects.get(user__email="guru.jkt@spi.local").teacher_name == "Ms. Linda"
    password = demo.ENV_FILE.read_text(encoding="utf-8").split("DEMO_PASSWORD=")[1].strip()
    assert users.get(email="finance.jkt@spi.local").check_password(password)


@pytest.mark.django_db
def test_seed_refuses_without_the_flags(settings):
    settings.DEBUG, settings.DEMO_ACCOUNTS = True, False
    with pytest.raises(CommandError, match="DEMO_ACCOUNTS"):
        call_command("seed_demo_accounts")


@pytest.mark.django_db
def test_login_panel_and_one_click_login(client, demo, branch, other_branch):
    call_command("seed_demo_accounts")
    page = client.get(reverse("accounts:login")).content.decode()
    password = demo.ENV_FILE.read_text(encoding="utf-8").split("DEMO_PASSWORD=")[1].strip()
    assert "Akun demo" in page and "cso.jkt@spi.local" in page and password not in page
    response = client.post(reverse("accounts:demo_login"), {"email": "cso.jkt@spi.local"})
    assert response.status_code == 302 and client.get("/").status_code == 200


@pytest.mark.django_db
def test_demo_login_is_closed_when_disabled_or_for_other_users(client, settings, make_user):
    make_user("bukan.demo@spi.test")
    settings.DEBUG, settings.DEMO_ACCOUNTS = True, False
    assert "Akun demo" not in client.get(reverse("accounts:login")).content.decode()
    assert client.post(reverse("accounts:demo_login"), {"email": "cso.jkt@spi.local"}).status_code == 404
    settings.DEMO_ACCOUNTS = True
    assert client.post(reverse("accounts:demo_login"), {"email": "bukan.demo@spi.test"}).status_code == 404
```

Run: `.venv/Scripts/python -m pytest accounts/tests/test_demo.py`
Expected: FAIL (`ModuleNotFoundError: No module named 'accounts.checks'`).

- [ ] **Step 2: Pengaturan & pemeriksaan sistem**

`spi_web/settings.py` — di bawah baris `SPI_EXCEL_DIR = ...` tambahkan:
```python
ENV_FILE = BASE_DIR / ".env"
DEMO_ACCOUNTS = env.bool("DEMO_ACCOUNTS", default=False)     # akun demo per peran - hanya untuk dicoba di laptop (DEBUG)
DEMO_PASSWORD = env("DEMO_PASSWORD", default="")
```

`accounts/checks.py`:
```python
from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security)
def demo_accounts_check(app_configs, **kwargs):
    if getattr(settings, "DEMO_ACCOUNTS", False) and not settings.DEBUG:
        return [Error("DEMO_ACCOUNTS hanya boleh aktif bila DEBUG=True (akun demo memakai satu kata sandi bersama).",
                      hint="Hapus DEMO_ACCOUNTS dari .env server.", id="spi.E001")]
    return []
```

`accounts/apps.py`:
```python
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"
    verbose_name = "Akun"

    def ready(self):
        from . import checks  # noqa: F401  (mendaftarkan pemeriksaan sistem)
```

- [ ] **Step 3: Akun demo & perintah**

`accounts/demo.py`:
```python
"""Akun demo per peran untuk mencoba aplikasi di laptop (spesifikasi dasbor gelombang 1 §5). Hanya bila DEBUG & DEMO_ACCOUNTS.
Kata sandi bersama disimpan di .env (DEMO_PASSWORD) - tidak pernah ditampilkan di halaman."""
import re
import secrets

from django.conf import settings
from django.utils import timezone

from accounts.models import User
from branches.models import Branch, Membership
from masterdata.models import TeacherMaster

DEMO_USERS = [
    {"email": "superadmin@spi.local", "name": "Demo Super Admin", "branch": None, "role": "SUPER_ADMIN"},
    {"email": "admin.jkt@spi.local", "name": "Demo Admin Jakarta", "branch": "SPI-JKT", "role": "BRANCH_ADMIN"},
    {"email": "manager.jkt@spi.local", "name": "Demo Manager Jakarta", "branch": "SPI-JKT", "role": "MANAGER"},
    {"email": "cso.jkt@spi.local", "name": "Demo CSO Jakarta", "branch": "SPI-JKT", "role": "CSO"},
    {"email": "finance.jkt@spi.local", "name": "Demo Finance Jakarta", "branch": "SPI-JKT", "role": "FINANCE"},
    {"email": "academic.jkt@spi.local", "name": "Demo Academic Jakarta", "branch": "SPI-JKT", "role": "ACADEMIC"},
    {"email": "guru.jkt@spi.local", "name": "Demo Guru Jakarta", "branch": "SPI-JKT", "role": "TEACHER"},
    {"email": "admin.as@spi.local", "name": "Demo Admin Alam Sutera", "branch": "SPI-AS", "role": "BRANCH_ADMIN"},
]
DEMO_EMAILS = {u["email"] for u in DEMO_USERS}
ROLE_TEXT = {"SUPER_ADMIN": "Super Admin", "BRANCH_ADMIN": "Branch Admin", "MANAGER": "Manager", "CSO": "CSO", "FINANCE": "Finance",
             "ACADEMIC": "Academic", "TEACHER": "Teacher"}


def demo_enabled():
    return bool(settings.DEBUG and getattr(settings, "DEMO_ACCOUNTS", False))


def ensure_password(env_file):
    """DEMO_PASSWORD dari .env; bila kosong dibuat acak sekali dan ditulis ke .env."""
    text = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
    m = re.search(r"^DEMO_PASSWORD=(.+)$", text, re.M)
    if m and m.group(1).strip():
        return m.group(1).strip()
    if getattr(settings, "DEMO_PASSWORD", ""):
        password = settings.DEMO_PASSWORD
    else:
        password = secrets.token_urlsafe(18)
    line = f"DEMO_PASSWORD={password}"
    text = re.sub(r"^DEMO_PASSWORD=.*$", line, text, flags=re.M) if m else (text.rstrip("\n") + "\n" + line + "\n").lstrip("\n")
    env_file.write_text(text, encoding="utf-8")
    return password


def seed(password):
    now, out = timezone.now(), []
    branches = {b.code: b for b in Branch.objects.filter(code__in={u["branch"] for u in DEMO_USERS if u["branch"]})}
    for spec in DEMO_USERS:
        branch = branches.get(spec["branch"]) if spec["branch"] else None
        if spec["branch"] and branch is None:
            out.append({**spec, "status": f"dilewati: cabang {spec['branch']} belum ada"})
            continue
        user = User.objects.filter(email=spec["email"]).first() or User(email=spec["email"])
        user.full_name, user.is_active, user.is_super_admin = spec["name"], True, spec["role"] == "SUPER_ADMIN"
        user.email_verified_at = user.email_verified_at or now
        user.set_password(password)
        user.save()
        if branch is not None:
            teacher = ""
            if spec["role"] == "TEACHER":
                first = TeacherMaster.objects.for_branch(branch).exclude(name="").order_by("row_no").first()
                teacher = first.name if first else "Guru Demo"
            Membership.objects.update_or_create(user=user, branch=branch, defaults={"role": spec["role"], "teacher_name": teacher})
        out.append({**spec, "status": "siap"})
    return out


def available():
    """Akun demo yang ada & aktif, untuk panel di halaman Masuk."""
    have = set(User.objects.filter(email__in=DEMO_EMAILS, is_active=True).values_list("email", flat=True))
    return [{**u, "role_text": ROLE_TEXT[u["role"]]} for u in DEMO_USERS if u["email"] in have]
```

`accounts/management/__init__.py`, `accounts/management/commands/__init__.py`: kosong.

`accounts/management/commands/seed_demo_accounts.py`:
```python
"""Buat / perbarui akun demo per peran (hanya DEBUG & DEMO_ACCOUNTS). Kata sandi: DEMO_PASSWORD di .env.
    .venv/Scripts/python manage.py seed_demo_accounts"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.demo import demo_enabled, ensure_password, seed


class Command(BaseCommand):
    help = "Akun demo per peran untuk mencoba aplikasi di laptop."

    def handle(self, *args, **opts):
        if not demo_enabled():
            raise CommandError("Akun demo hanya untuk laptop: set DEBUG=True dan DEMO_ACCOUNTS=True di .env.")
        for row in seed(ensure_password(settings.ENV_FILE)):
            self.stdout.write(f"  {row['email']:28} {row['role']:13} {row['branch'] or 'semua cabang':10} {row['status']}")
        self.stdout.write(self.style.SUCCESS("Selesai. Kata sandi bersama: lihat DEMO_PASSWORD di file .env (tidak ditampilkan)."))
```

- [ ] **Step 4: Panel & masuk satu klik**

`accounts/views.py` — tambahkan impor `from django.http import Http404`, `from django.views.decorators.http import require_POST`, `from . import demo`; di `login_view` ganti baris `return render(request, "accounts/login.html", {"form": form})` dengan:
```python
    return render(request, "accounts/login.html", {"form": form, "demo_users": demo.available() if demo.demo_enabled() else []})
```
dan tambahkan di akhir berkas:
```python
@require_POST
def demo_login_view(request):
    """Masuk satu klik untuk akun demo - hanya DEBUG & DEMO_ACCOUNTS, hanya email daftar demo."""
    email = request.POST.get("email", "").strip().lower()
    if not demo.demo_enabled() or email not in demo.DEMO_EMAILS:
        raise Http404
    user = User.objects.filter(email=email, is_active=True).first()
    if user is None:
        raise Http404
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return redirect("core:home")
```

`accounts/urls.py` — tambahkan `path("masuk/demo/", views.demo_login_view, name="demo_login"),` setelah baris `masuk/`.

`accounts/templates/accounts/login.html` — sebelum `{% endblock %}` tambahkan:
```django
{% if demo_users %}
<div class="mt-8 rounded-xl border border-dashed border-amber-300 bg-amber-50 p-4">
  <p class="flex items-center gap-2 text-sm font-bold text-amber-900"><i class="ti ti-flask" aria-hidden="true"></i>Akun demo (laptop ini saja)</p>
  <p class="mt-1 text-xs text-amber-800">Klik peran untuk langsung masuk. Daftar & kata sandi: docs/AKUN_DEMO.md dan DEMO_PASSWORD di .env.</p>
  <div class="mt-3 grid gap-2 sm:grid-cols-2">
    {% for u in demo_users %}
      <form method="post" action="{% url 'accounts:demo_login' %}">{% csrf_token %}<input type="hidden" name="email" value="{{ u.email }}">
        <button class="w-full rounded-lg border border-amber-200 bg-white px-3 py-2 text-left text-sm hover:border-amber-400">
          <span class="block font-semibold text-slate-800">{{ u.role_text }}{% if u.branch %} · {{ u.branch }}{% endif %}</span>
          <span class="block text-xs text-slate-500">{{ u.email }}</span></button>
      </form>
    {% endfor %}
  </div>
</div>
{% endif %}
```

`docs/AKUN_DEMO.md`:
```markdown
# Akun demo (laptop)

Akun demo dipakai untuk mencoba aplikasi sendiri di laptop. **Jangan aktifkan di server** — pemeriksaan sistem `spi.E001`
menolak `DEMO_ACCOUNTS=True` tanpa `DEBUG=True`.

## Menyalakan

1. Di `.env`: `DEBUG=True` dan `DEMO_ACCOUNTS=True`.
2. Pastikan cabang SPI-JKT (dan SPI-AS) sudah diimpor (lihat README).
3. `.venv/Scripts/python manage.py seed_demo_accounts` — membuat/memperbarui akun di bawah. Bila `DEMO_PASSWORD` di `.env`
   kosong, kata sandi acak dibuat dan ditulis ke `.env`. Perintah boleh diulang.
4. Halaman Masuk menampilkan panel **Akun demo**: klik peran untuk langsung masuk; atau masuk biasa dengan email di bawah dan
   kata sandi `DEMO_PASSWORD` dari `.env`.

| Email | Peran | Cabang | Yang terlihat |
|---|---|---|---|
| superadmin@spi.local | Super Admin | semua | semua halaman, menu Cabang |
| admin.jkt@spi.local | Branch Admin | SPI Jakarta | Beranda, Laporan, Impor Data, Pengguna |
| manager.jkt@spi.local | Manager | SPI Jakarta | Beranda, Laporan |
| cso.jkt@spi.local | CSO | SPI Jakarta | Beranda, Laporan |
| finance.jkt@spi.local | Finance | SPI Jakarta | Beranda, Laporan |
| academic.jkt@spi.local | Academic | SPI Jakarta | Beranda, Laporan |
| guru.jkt@spi.local | Teacher | SPI Jakarta | belum ada halaman (tahap jadwal guru) — tampil "tidak punya akses" |
| admin.as@spi.local | Branch Admin | SPI Alam Sutera | cabang tanpa data operasional: angka nol / "—" |

Mematikan: hapus `DEMO_ACCOUNTS` dari `.env` (panel hilang, masuk satu klik ditolak). Akun tetap ada sampai dinonaktifkan di
halaman Pengguna & Akses.
```

- [ ] **Step 5: Jalankan uji**

Run:
```bash
.venv/Scripts/python -m pytest
.venv/Scripts/python manage.py check
```
Expected: semua uji cepat lulus (termasuk `accounts/tests/test_demo.py` 6 passed); `System check identified no issues`.

- [ ] **Step 6: Commit**

```bash
git add spi_web accounts docs/AKUN_DEMO.md
git commit -m "feat: akun demo per peran (hanya DEBUG & DEMO_ACCOUNTS) - perintah seed, panel masuk satu klik" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Verifikasi menyeluruh, data laptop, dokumentasi

**Files:**
- Modify: `README.md`, `..\00_SYSTEM\CHANGE_LOG\CHANGE_LOG.md` (baris baru, CRLF dipertahankan), `.env` (lokal, tidak di-commit)

- [ ] **Step 1: Seluruh uji**

Run:
```bash
.venv/Scripts/python -m pytest
.venv/Scripts/python -m pytest -m slow
```
Expected: semua lulus (uji cepat + uji lambat importer & angka emas dashboards).

- [ ] **Step 2: Data laptop & akun demo**

Run:
```bash
.venv/Scripts/python scripts/devdb.py start
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py import_workbook ../APP/SPI_STUDENT-SPP_APP_2026_09_v4.xlsm --branch SPI-JKT --commit --replace
.venv/Scripts/python manage.py import_workbook ../APP/SPI_ALAM_SUTERA_v4.xlsm --branch SPI-AS --create --commit --replace
```
Tambahkan `DEBUG=True` dan `DEMO_ACCOUNTS=True` ke `.env` bila belum ada, lalu:
```bash
.venv/Scripts/python manage.py seed_demo_accounts
```
Expected: impor ulang tanpa error (kolom Dihitung kini terisi); 8 akun `siap`.

- [ ] **Step 3: Periksa di browser (desktop & 375 px)**

Jalankan server lewat konfigurasi `spi-web` (`.claude/launch.json`), masuk lewat panel Akun demo:
- CSO Jakarta: Beranda — Murid aktif 154, SPP diterima Sep 2026 Rp 69.051.000, Murid OFF 118, Kelas aktif 106, Masalah kritis 2 (angka emas HOME); cari "aby" menampilkan hasil; 3 kartu "menyusul".
- Laporan bawaan (Sep 2026): kartu murid 157 / 154 / 3 / 0 / 3 / 36 / 9; SPP Rp 69.051.000 / Rp 765.383.125 / 154 / 76 · 49% / 78 / 4 / 133; 7 grafik tergambar; klik batang "Off" → daftar tersaring; tombol kembali browser memulihkan filter; ganti bulan ke Jun 2024 → kartu SPP "—"; Agu 2026 → angka (jurnal sudah diputuskan di workbook? bila SETTINGS = BELUM DIPUTUSKAN → "perlu keputusan").
- Admin Alam Sutera: Beranda & Laporan tanpa error.
- Guru Jakarta: "tidak punya akses" (403).
- Lebar 375 px: kartu satu kolom, tabel bergulir, tidak ada geser halaman horizontal; konsol tanpa error.

- [ ] **Step 4: Dokumentasi**

`README.md` — tambahkan bagian:
```markdown
## Dasbor (gelombang 1)

- **Beranda** (`/`): situasi sekarang seperti HOME Excel (murid aktif, SPP bulan buku kas terakhir, OFF, kelas, masalah kritis,
  bukti bayar), cari murid sambil mengetik. Kartu "menyusul" = logika belum dibangun.
- **Laporan Murid & SPP** (`/laporan/`): filter bulan/program/tipe/mode/guru (tanpa muat ulang), kartu KPI, 7 grafik, daftar
  perhatian, daftar murid, periode operasional v4. Angka = DASHBOARD Excel.
- Angka emas: `python tools/export_golden.py` (Python sistem + pywin32, Excel terpasang) menghitung ulang salinan workbook Jakarta
  dan menulis `dashboards/tests/golden/jkt_golden.json`; `.venv/Scripts/python -m pytest -m slow dashboards` membandingkan tanpa
  toleransi.
- Akun demo untuk dicoba di laptop: `docs/AKUN_DEMO.md`.
- Aset tampilan lokal: `npm run vendor` (htmx, Alpine, Chart.js, Plus Jakarta Sans, Tabler Icons) lalu `npm run build:css`.
```

`..\00_SYSTEM\CHANGE_LOG\CHANGE_LOG.md` — tambahkan satu baris tabel setelah baris terakhir (nomor berikutnya, tanggal 2026-10-02) dengan format baris sebelumnya: "app web: dasbor gelombang 1 — sistem desain gaya B, Beranda & Laporan Murid & SPP (angka = Excel, diuji angka emas), perbaikan impor kolom Dihitung BUKU_KAS, akun demo per peran (laptop)". Pertahankan akhir baris CRLF.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: README dasbor gelombang 1 - Beranda, Laporan, angka emas, akun demo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
