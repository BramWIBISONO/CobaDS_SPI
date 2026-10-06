"""Branch-scoped, traceable data for the Management Center."""
from dashboards.calc.base import KAS_START, fixed, label, period_code, same
from dashboards.calc.kas import kas_rows, perlu_keputusan
from dashboards.calc.operasional import kritis
from finance.models import BuktiBayar, NotaLog, SppTagihan
from classes.models import Kehadiran
from students.services import is_open_followup

from .lifecycle import KOSONG, kpi_bulan, months_until, wawasan

INSIGHT_GROUPS = (
    ("mendekati_off", "Cuti berulang"),
    ("baru_off", "Baru menjadi OFF"),
    ("kembali", "Kembali dari OFF"),
    ("lama_tidak_aktif", "Lama tidak aktif"),
    ("status_kosong", "Status kosong terbaru"),
    ("tidak_biasa", "Perubahan status tidak biasa"),
)


def build_overview(data, month, rows, month_index):
    """Summarize lifecycle, finance-source, and operational records without estimates."""
    current = kpi_bulan(rows, month_index)
    previous = kpi_bulan(rows, month_index - 1) if month_index else None
    previous_year = kpi_bulan(rows, month_index - 12) if month_index >= 12 else None
    status_missing = sum(row.huruf[month_index] == KOSONG for row in rows)
    lifecycle_insights = wawasan(data, rows)
    attention_groups = [
        {"title": title, "items": lifecycle_insights[key]}
        for key, title in INSIGHT_GROUPS
        if lifecycle_insights[key]
    ]
    period = period_code(month)
    all_months = months_until(data.today)
    trend = []
    for index in range(max(0, month_index - 11), month_index + 1):
        metrics = kpi_bulan(rows, index)
        trend.append({"label": label(all_months[index]), "active": metrics["aktif"]})
    max_active = max((point["active"] for point in trend), default=0)
    for point in trend:
        point["height"] = max(3, round(point["active"] * 100 / max_active)) if max_active else 3

    invoices = SppTagihan.objects.for_branch(data.branch).filter(per=period).count()
    payment_rows = list(BuktiBayar.objects.for_branch(data.branch).filter(per=period))
    nota_count = NotaLog.objects.for_branch(data.branch).count()
    cash_periods = data.kas_months
    cash_available = month in cash_periods and month >= KAS_START and not perlu_keputusan(data, month)
    recognized_rows = [row for row in kas_rows(data) if row.masuk_spp(month)] if cash_available else []
    received = sum(row.row.nominal or 0 for row in recognized_rows)
    allocated = sum(sum(row.b) for row in recognized_rows)
    pending_verification = sum(1 for row in payment_rows if same(row.ver, "Belum Diverifikasi"))
    payment_needs_review = sum(
        1 for row in payment_rows if same(row.ver, "Tidak Cocok") or same(row.ver, "Perlu Klarifikasi")
    )

    sessions = [session for session in data.sesi if same(session.per, period)]
    realized = [session for session in sessions if same(session.status, "REALIZED") or same(session.status, "MAKE-UP")]
    scheduled = [session for session in sessions if same(session.status, "SCHEDULED")]
    cancelled = sum(1 for session in sessions if same(session.status, "CANCELLED"))
    attendance_sessions = (
        Kehadiran.objects.filter(branch=data.branch, sid__in=[session.sid for session in realized])
        .values("sid").distinct().count()
        if realized else 0
    )
    open_followups = [item for item in data.followups if is_open_followup(item)]
    overdue_followups = sum(1 for item in open_followups if item.next and item.next <= data.today)

    return {
        "period": month,
        "student_count": len(rows),
        "current": current,
        "previous": previous,
        "previous_year": previous_year,
        "status_missing": status_missing,
        "trend": trend,
        "attention_groups": attention_groups,
        "finance": {
            "cash_rows": len(data.kas),
            "invoice_rows": invoices,
            "payment_rows": len(payment_rows),
            "nota_rows": nota_count,
            "received_available": cash_available,
            "received": fixed(received) if cash_available else None,
            "unallocated": fixed(received - allocated) if cash_available else None,
            "received_note": (
                "Diakui dari BukuKas memakai aturan SPP yang sudah ada."
                if cash_available else
                "Tidak tersedia untuk periode ini: tidak ada baris BukuKas periode tersebut, periode sebelum cakupan BukuKas, atau jurnal menunggu keputusan."
            ),
            "billing_available": invoices > 0,
            "pending_verification": pending_verification,
            "needs_review": payment_needs_review,
        },
        "operations": {
            "sessions": len(sessions),
            "realized": len(realized),
            "scheduled": len(scheduled),
            "cancelled": cancelled,
            "attendance_sessions": attendance_sessions,
            "attendance_rate": round(attendance_sessions * 100 / len(realized), 1) if realized else None,
            "open_followups": len(open_followups),
            "overdue_followups": overdue_followups,
            "critical_issues": kritis(data),
        },
    }
