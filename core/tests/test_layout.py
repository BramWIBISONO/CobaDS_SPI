"""Tabel harus bisa digeser di layar sempit (375 px): setiap <table> berada di dalam wadah yang bisa digulir."""
from html.parser import HTMLParser

import pytest
from django.urls import reverse

from importer.models import ImportRun

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
SCROLL = ("overflow-x-auto", "overflow-auto", "overflow-y-auto")


class TableWrappers(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.unscrollable = [], 0

    def handle_starttag(self, tag, attrs):
        if tag == "table" and not any(any(s in cls for s in SCROLL) for _t, cls in self.stack):
            self.unscrollable += 1
        if tag not in VOID:
            self.stack.append((tag, dict(attrs).get("class") or ""))

    def handle_endtag(self, tag):
        while self.stack:
            if self.stack.pop()[0] == tag:
                break


def unscrollable_tables(response):
    parser = TableWrappers()
    parser.feed(response.content.decode())
    return parser.unscrollable


@pytest.mark.django_db
def test_admin_tables_scroll_on_narrow_screens(client, branch, make_user):
    client.force_login(make_user("boss@spi.test", super_admin=True))
    client.post(reverse("core:switch_branch"), {"branch": branch.pk})
    run = ImportRun.objects.create(branch=branch, original_name="jkt.xlsm", sha256="0" * 64, report={
        "ok": False, "fatal": "", "unit": "UNIT-AS", "counts": {"STUDENT_MASTER": 1}, "existing": {}, "errors": 1, "warnings": 0,
        "issues": [{"level": "error", "table": "SETTINGS", "row": None, "field": "Unit", "message": "bukan UNIT-JKT"}],
        "issues_hidden": 0})
    pages = [reverse("accounts:users"), reverse("importer:upload"), reverse("importer:preview", args=[run.pk]), reverse("branches:list"), reverse("dashboards:laporan")]
    for url in pages:
        response = client.get(url)
        assert response.status_code == 200, url
        assert unscrollable_tables(response) == 0, url
