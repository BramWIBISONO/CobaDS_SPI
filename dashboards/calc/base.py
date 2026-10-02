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
CHART_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]   # urutan tetap
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


def fixed(x):
    """FIXED(x, 0) Excel dengan pemisah ribuan Indonesia (titik)."""
    return f"{round_half_up(x):,}".replace(",", ".")


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


def chart(id, title, labels, series, *, type="bar", horizontal=False, stacked=False, money=False, links=None, note="", height=""):
    """Kartu grafik: series = [(label, data)]; warna kategori diberikan berurutan (tidak pernah diulang)."""
    if len(series) > len(CHART_COLORS):
        raise ValueError("lebih dari 8 seri - gabungkan ke 'Lainnya' atau pecah grafiknya")
    links = links or [None] * len(labels)
    s = [{"label": lab, "data": data, "color": CHART_COLORS[i]} for i, (lab, data) in enumerate(series)]
    return {"id": id, "title": title, "type": type, "labels": labels, "series": s, "horizontal": horizontal, "stacked": stacked,
            "money": money, "links": links, "note": note, "height": height,
            "rows": [{"label": lab, "link": links[i], "values": [x["data"][i] for x in s]} for i, lab in enumerate(labels)]}
