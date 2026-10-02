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
