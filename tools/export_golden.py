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
