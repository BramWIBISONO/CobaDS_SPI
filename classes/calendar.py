"""Tata letak kalender sesi - presentasi saja (tidak mengubah data): posisi blok sesi di kisi jam, jalur berdampingan untuk sesi
yang bertumpuk pada jam yang sama, garis "sekarang", dan kisi bulan. Satu jam = HOUR_PX piksel."""
import calendar as _cal
import datetime

from dashboards.calc.base import as_date

HOUR_PX = 64
MIN_MINUTES = 30                      # blok sesi paling pendek yang digambar (agar teks terbaca)
DEFAULT_HOURS = (8, 18)
TYPES = ("P", "G", "F", "S")          # huruf pertama kode kelas = tipe (Partner, Group, Focus, School)


def _minutes(t):
    return t.hour * 60 + t.minute


def session_type(ses):
    letter = (ses.kode or "")[:1].upper()
    return letter if letter in TYPES else "X"


def hour_range(sessions):
    """(jam awal, jam akhir) kisi: minimal 08-18, diperluas agar semua sesi muat."""
    lo, hi = DEFAULT_HOURS
    for s in sessions:
        if s.mulai:
            lo = min(lo, s.mulai.hour)
            end = s.selesai or s.mulai
            hi = max(hi, end.hour + (1 if end.minute else 0), s.mulai.hour + 1)
    return lo, min(24, hi)


def lay_out_day(items, start_hour, max_lanes=None, day=None, day_url=None):
    """items: [{'s': Sesi, ...}] -> item + top/height (px) + left/width (%) per sesi berjam; sesi tanpa jam dikembalikan terpisah.
    Sesi yang tumpang tindih dibagi ke jalur berdampingan (lebar = 100% / jumlah jalur di gugusnya).
    Bila max_lanes ditentukan (mis. 3 untuk tampilan minggu) dan tumpukan > max_lanes:
    jalur terakhir menampilkan blok overflow '+N sesi' yang mengarah ke tampilan hari detail."""
    timed = [it for it in items if it["s"].mulai]
    untimed = [it for it in items if not it["s"].mulai]

    def span(it):
        st = _minutes(it["s"].mulai)
        en = _minutes(it["s"].selesai) if it["s"].selesai else st + 60
        return st, max(en, st + MIN_MINUTES)

    timed.sort(key=lambda it: (span(it)[0], -span(it)[1], it["s"].sid))
    placed, cluster, lane_ends, cluster_end = [], [], [], -1

    def close(group, lanes):
        if max_lanes and lanes > max_lanes:
            vis_lanes = max_lanes
            keep_lanes = max_lanes - 1
            normal = [it for it in group if it["lane"] < keep_lanes]
            overflow = [it for it in group if it["lane"] >= keep_lanes]
            for it in normal:
                it["width"] = round(100 / vis_lanes, 3)
                it["left"] = round(it["lane"] * 100 / vis_lanes, 3)
                it["lanes"] = vis_lanes
                it["is_overflow"] = False
            placed.extend(normal)

            if overflow:
                top = min(it["top"] for it in overflow)
                max_bottom = max(it["top"] + it["height"] for it in overflow)
                height = max(MIN_MINUTES * HOUR_PX / 60 - 3, max_bottom - top)
                target_url = day_url or ""
                if not target_url and day:
                    target_url = f"?tampilan=hari&tanggal={day.isoformat()}"
                placed.append({
                    "is_overflow": True,
                    "overflow_count": len(overflow),
                    "top": top,
                    "height": height,
                    "left": round(keep_lanes * 100 / vis_lanes, 3),
                    "width": round(100 / vis_lanes, 3),
                    "lanes": vis_lanes,
                    "url": target_url,
                    "compact": height < 45,
                    "s": None,
                })
        else:
            for it in group:
                it["width"] = round(100 / lanes, 3)
                it["left"] = round(it["lane"] * 100 / lanes, 3)
                it["lanes"] = lanes
                it["is_overflow"] = False
            placed.extend(group)

    for it in timed:
        st, en = span(it)
        if cluster and st >= cluster_end:
            close(cluster, len(lane_ends))
            cluster, lane_ends = [], []
        lane = next((i for i, end in enumerate(lane_ends) if end <= st), None)
        if lane is None:
            lane = len(lane_ends)
            lane_ends.append(en)
        else:
            lane_ends[lane] = en
        it["lane"] = lane
        it["top"] = round((st - start_hour * 60) * HOUR_PX / 60, 1)
        it["height"] = round((en - st) * HOUR_PX / 60 - 3, 1)
        it["compact"] = (en - st) < 45
        cluster.append(it)
        cluster_end = max(cluster_end, en)
    if cluster:
        close(cluster, len(lane_ends))
    return placed, untimed


def now_offset(day, now, start_hour, end_hour):
    """Posisi garis 'sekarang' (px) bila hari itu hari ini dan jamnya di dalam kisi; selain itu None."""
    if day != now.date() or not (start_hour * 60 <= _minutes(now) <= end_hour * 60):
        return None
    return round((_minutes(now) - start_hour * 60) * HOUR_PX / 60, 1)


def month_weeks(anchor, items_by_day, today, per_cell=3):
    """Kisi bulan (Senin-Minggu) yang memuat bulan `anchor`: [[{date, in_month, is_today, items, more, count}]*7]."""
    first = anchor.replace(day=1)
    last = first.replace(day=_cal.monthrange(first.year, first.month)[1])
    start = first - datetime.timedelta(days=first.weekday())
    end = last + datetime.timedelta(days=6 - last.weekday())
    weeks, week, d = [], [], start
    while d <= end:
        items = items_by_day.get(d, [])
        week.append({"date": d, "in_month": d.month == first.month, "is_today": d == today, "items": items[:per_cell],
                     "more": max(0, len(items) - per_cell), "count": len(items)})
        if len(week) == 7:
            weeks.append(week)
            week = []
        d += datetime.timedelta(days=1)
    return weeks


def month_bounds(anchor):
    first = anchor.replace(day=1)
    last = first.replace(day=_cal.monthrange(first.year, first.month)[1])
    return first - datetime.timedelta(days=first.weekday()), last + datetime.timedelta(days=6 - last.weekday())


def shift_month(d, n):
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    return datetime.date(y, m, min(d.day, _cal.monthrange(y, m)[1]))


def group_by_day(rows):
    out = {}
    for s in rows:
        out.setdefault(as_date(s.tgl), []).append(s)
    return out
