"""Nilai sel Excel -> nilai field. Tidak ada nilai yang ditebak: teks di kolom angka/tanggal hanya diterima bila kolom itu 'campur'
(disimpan di <nama>_text, kolom bertipe kosong - sama seperti ISNUMBER / ISTEXT di Excel)."""
import datetime
from zoneinfo import ZoneInfo

from django.conf import settings


class ConvertError(ValueError):
    pass


def _tz():
    return ZoneInfo(settings.TIME_ZONE)


def _as_text(raw):
    if isinstance(raw, bool):
        return "TRUE" if raw else "FALSE"
    if isinstance(raw, float) and raw.is_integer():
        return str(int(raw))
    if isinstance(raw, datetime.datetime):
        return raw.isoformat(sep=" ")
    return str(raw)


def _typed(kind, raw):
    if kind == "number":
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ConvertError(f"bukan angka: {raw!r}")
        return float(raw)
    if kind == "date":
        if isinstance(raw, datetime.datetime):
            return raw.date()
        if isinstance(raw, datetime.date):
            return raw
        raise ConvertError(f"bukan tanggal: {raw!r}")
    if kind == "datetime":
        if isinstance(raw, datetime.datetime):
            value = raw
        elif isinstance(raw, datetime.date):
            value = datetime.datetime(raw.year, raw.month, raw.day)
        else:
            raise ConvertError(f"bukan tanggal & jam: {raw!r}")
        return value if value.tzinfo else value.replace(tzinfo=_tz())
    if kind == "time":
        if isinstance(raw, datetime.datetime):
            return raw.time()
        if isinstance(raw, datetime.time):
            return raw
        if isinstance(raw, (int, float)) and not isinstance(raw, bool) and 0 <= raw < 1:
            seconds = round(raw * 86400)
            return datetime.time(seconds // 3600, seconds % 3600 // 60, seconds % 60)
        raise ConvertError(f"bukan jam: {raw!r}")
    if kind == "bool":
        if isinstance(raw, bool):
            return raw
        raise ConvertError(f"bukan TRUE/FALSE: {raw!r}")
    raise ConvertError(f"jenis kolom tidak dikenal: {kind}")


def convert(field, raw):
    out = {field.text_field: ""} if field.text_field else {}
    if raw is None or raw == "":
        out[field.name] = "" if field.kind == "text" else None
        return out
    if field.kind == "text":
        out[field.name] = _as_text(raw)
        return out
    try:
        out[field.name] = _typed(field.kind, raw)
    except ConvertError:
        if field.text_field and isinstance(raw, str):
            out[field.name] = None
            out[field.text_field] = raw
            return out
        raise
    return out
