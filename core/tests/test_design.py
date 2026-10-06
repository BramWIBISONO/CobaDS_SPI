from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string

from dashboards.templatetags.spi import angka, ikon_status, rp, tone_status

STATIC = Path(settings.BASE_DIR) / "static"


def test_local_assets_are_present():
    for rel in ("vendor/chart.umd.min.js", "vendor/tabler/tabler-icons.min.css", "vendor/fonts/inter-latin-wght-normal.woff2",
                "js/dashboards.js", "js/app.js", "img/spi-mark.png", "img/favicon-32.png"):
        assert (STATIC / rel).is_file(), rel
    assert any((STATIC / "vendor/tabler/fonts").glob("tabler-icons.woff2*"))


def test_design_tokens_and_components_are_built():
    """Satu design system: token netral + biru SPI, komponen bersama; warna per topik (gaya B lama) tidak ada lagi."""
    css = (STATIC / "css/app.css").read_text(encoding="utf-8")
    for token in ("Inter Variable", "--color-canvas", "--color-brand-500", "--color-ink", "--color-line", "--shadow-sm", "--radius-xl"):
        assert token in css, token
    for component in (".btn-primary", ".field", ".card", ".kpi", ".status-badge", ".data-table", ".tabs", ".segmented", ".avatar",
                      ".menu", ".toast", ".empty", ".skeleton", ".app-sidebar", ".app-topbar", ".cal-event", ".action-item", ".pay-overdue", ".hero", ".tile-violet", ".pring", ".week-strip", ".cover", ".class-band"):
        assert component in css, component
    assert ".tone-spp" not in css and "Plus Jakarta Sans" not in css


from decimal import Decimal


def test_number_filters_follow_indonesian_format():
    assert (angka(1234567), angka(1234.5), angka("—"), angka(None), angka(Decimal("670000.00"))) == ("1.234.567", "1.235", "—", "", "670.000")
    assert (rp(69051000), rp("perlu keputusan"), rp(None), rp(Decimal("670000.00"))) == ("Rp 69.051.000", "perlu keputusan", "—", "Rp 670.000")
    assert [tone_status(s) for s in ("Aktif", "Baru", "Rejoin", "Cuti", "Off", "ACTIVE", "ON LEAVE", "OFF", "PENDING", "x")] == \
        ["baik", "baik", "baik", "perhatian", "kritis", "baik", "perhatian", "kritis", "serius", "netral"]
    assert ikon_status("Off") == "circle-x" and ikon_status("Aktif") == "circle-check"


def test_kpi_card_renders_value_or_soon():
    html = render_to_string("components/kpi_card.html", {"tone": "spp", "icon": "cash", "label": "SPP diterima", "value": "Rp 1",
                                                          "sub": "buku kas", "href": "/laporan/"})
    assert 'class="kpi ' in html and "ti-cash" in html and "Rp 1" in html and 'href="/laporan/"' in html and "tone-" not in html
    assert "kpi-danger" in render_to_string("components/kpi_card.html", {"tone": "kritis", "icon": "x", "label": "Off", "value": "3"})
    soon = render_to_string("components/kpi_card.html", {"tone": "kritis", "icon": "list-check", "label": "Perlu tindakan", "soon": True})
    assert "kpi-muted" in soon and "menyusul" in soon and "kpi-danger" not in soon


def test_chart_card_has_data_table_and_legend():
    from dashboards.calc.base import chart

    c = chart("c-status", "Status murid", ["Aktif", "Off"], [("Murid", [5, 2])], links=["/laporan/?daftar=aktif", None])
    html = render_to_string("components/chart_card.html", {"chart": c})
    assert 'data-chart="c-status"' in html and 'id="c-status"' in html and "<table" in html
    assert 'href="/laporan/?daftar=aktif"' in html and "Status murid" in html and c["series"][0]["color"] == "#2a78d6"


def test_chart_script_draws_charts_from_the_json_spec():
    js = (STATIC / "js/dashboards.js").read_text(encoding="utf-8")
    assert "window.SPICharts" in js and "new Chart(" in js and "htmx:afterSettle" in js


@pytest.mark.django_db
def test_chart_library_loads_only_on_pages_with_charts(client, branch, make_user):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    assert "chart.umd.min.js" not in client.get("/").content.decode()
    assert "chart.umd.min.js" in client.get("/laporan/").content.decode()
