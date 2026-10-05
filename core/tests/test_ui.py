import pytest
from django.template import Context, Template
from django.test import RequestFactory

from core.ui import paginate, sort_key

rf = RequestFactory()


def render(src, **ctx):
    return Template("{% load ui %}" + src).render(Context(ctx))


def test_paginate_clamps_bad_and_large_page_numbers():
    items = list(range(60))
    assert list(paginate(rf.get("/?page=3"), items, 25).object_list) == list(range(50, 60))
    assert paginate(rf.get("/?page=abc"), items, 25).number == 1
    assert paginate(rf.get("/?page=99"), items, 25).number == 3
    assert paginate(rf.get("/"), [], 25).paginator.count == 0


def test_sort_key_accepts_only_known_columns():
    allowed = {"nama": "nama", "status": "status"}
    assert sort_key(rf.get("/?sort=-status"), allowed, "nama") == ("status", True)
    assert sort_key(rf.get("/?sort=drop table"), allowed, "nama") == ("nama", False)


def test_qs_replaces_one_parameter_and_keeps_the_rest():
    request = rf.get("/murid/?q=ani&status=ACTIVE&page=4")
    out = render('{% qs request page=2 %}|{% qs request sort="nama" page=None %}', request=request)
    assert out == "?q=ani&amp;status=ACTIVE&amp;page=2|?q=ani&amp;status=ACTIVE&amp;sort=nama"


def test_sort_header_toggles_direction_and_marks_aria_sort():
    request = rf.get("/murid/?sort=nama&q=a")
    html = render('{% sort_th request "nama" "Nama" %}{% sort_th request "status" "Status" %}', request=request)
    assert 'aria-sort="ascending"' in html and "sort=-nama" in html and "sort=status" in html and "q=a" in html


def test_page_header_renders_breadcrumb_title_and_actions():
    html = render('{% pageheader title="Murid" subtitle="Semua murid cabang" icon="users" %}<a class="btn">Tambah</a>{% endpageheader %}',
                  crumbs=[("Beranda", "/"), ("Murid", None)])
    assert "<h1" in html and "Murid" in html and "Semua murid cabang" in html and '<a class="btn">Tambah</a>' in html
    assert 'aria-label="Breadcrumb"' in html and 'href="/"' in html and "ti-users" in html


@pytest.mark.django_db
def test_base_layout_has_confirm_dialog_toasts_and_loading_bar(client, branch, make_user):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    html = client.get("/").content.decode()
    assert 'id="confirm-dialog"' in html and "js/app.js" in html and 'id="loading-bar"' in html and 'id="toasts"' in html
