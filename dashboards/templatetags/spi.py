"""Format angka Indonesia dan warna status untuk templat dasbor."""
from django import template

from dashboards.calc.base import fixed, fold

register = template.Library()

TONE = {"aktif": "baik", "baru": "baik", "rejoin": "baik", "active": "baik", "sudah ada pembayaran": "baik",
        "cuti": "perhatian", "on leave": "perhatian", "belum ada pembayaran": "perhatian", "perlu keputusan": "perhatian",
        "pending": "serius", "off": "kritis", "alumni/inactive": "netral",
        "realized": "baik", "make-up": "perhatian", "cancelled": "kritis", "scheduled": "netral",
        "hadir": "baik", "terlambat": "perhatian", "izin": "netral", "absen": "kritis",
        "verified": "baik", "belum diverifikasi": "perhatian", "tidak cocok": "kritis", "perlu klarifikasi": "serius",
        "sudah dibayar": "baik", "menunggu verifikasi": "perhatian", "belum dibayar": "serius", "terlambat bayar": "kritis",
        "belum jatuh tempo": "netral", "dibatalkan": "netral", "dibebaskan": "netral", "ditunda": "netral",
        "open": "baik", "closing": "perhatian", "closed": "netral"}
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
