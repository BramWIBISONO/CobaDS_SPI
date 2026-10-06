"""Komponen UI bersama: header halaman (dengan breadcrumb & aksi), header kolom yang bisa diurutkan, query string."""
from urllib.parse import urlencode

from django import template
from django.http import QueryDict
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


def _query(request, **changes):
    params = request.GET.copy() if request is not None else QueryDict(mutable=True)
    for key, value in changes.items():
        if value is None:
            params.pop(key, None)
        else:
            params[key] = value
    items = [(k, v) for k in params for v in params.getlist(k)]
    return "?" + urlencode(items) if items else "?"


@register.simple_tag
def qs(request, **changes):
    """Query string halaman ini dengan beberapa parameter diganti (None = dihapus)."""
    return _query(request, **changes)


@register.simple_tag
def sort_th(request, key, label, css=""):
    current = (request.GET.get("sort") or "") if request is not None else ""
    asc, desc = current == key, current == f"-{key}"
    target = f"-{key}" if asc else key
    aria = "ascending" if asc else "descending" if desc else "none"
    icon = "ti-arrow-up" if asc else "ti-arrow-down" if desc else "ti-arrows-sort"
    return format_html('<th class="{}" aria-sort="{}"><a href="{}" class="inline-flex items-center gap-1 hover:text-slate-800">{}'
                       '<i class="ti {} text-xs" aria-hidden="true"></i></a></th>', css, aria, _query(request, sort=target, page=None),
                       label, icon)


class PageHeaderNode(template.Node):
    def __init__(self, kwargs, nodelist):
        self.kwargs, self.nodelist = kwargs, nodelist

    def render(self, context):
        values = {k: v.resolve(context) for k, v in self.kwargs.items()}
        actions = mark_safe(self.nodelist.render(context).strip())
        tpl = context.template.engine.get_template("components/page_header.html")
        with context.push(**values, actions=actions):
            return tpl.render(context)


@register.tag("pageheader")
def do_pageheader(parser, token):
    """{% pageheader title=".." subtitle=".." icon=".." %}<tombol aksi>{% endpageheader %}; breadcrumb dari variabel `crumbs`."""
    kwargs = {}
    for bit in token.split_contents()[1:]:
        key, _, value = bit.partition("=")
        kwargs[key] = parser.compile_filter(value)
    nodelist = parser.parse(("endpageheader",))
    parser.delete_first_token()
    return PageHeaderNode(kwargs, nodelist)


@register.filter
def split(value, sep=None):
    return str(value).split(sep)


@register.filter
def getfield(form, name):
    """Bound field `name` dari form, atau None bila form tidak punya kolom itu."""
    try:
        return form[name]
    except KeyError:
        return None


@register.filter
def get(mapping, key):
    try:
        return mapping.get(key, "")
    except AttributeError:
        return ""


@register.filter
def sections(form):
    """[(judul, [nama kolom])] dari atribut `sections` form; bila tidak ada: satu bagian berisi semua kolom."""
    spec = getattr(form, "sections", None)
    if not spec:
        return [("", list(form.fields))]
    listed = {n for _t, names in spec for n in names}
    rest = [n for n in form.fields if n not in listed]
    out = [(title, [n for n in names if n in form.fields]) for title, names in spec] + [("", rest)]
    return [(title, names) for title, names in out if names]


@register.filter
def is_wide(bound_field):
    widget = bound_field.field.widget
    return widget.__class__.__name__ in ("Textarea", "CheckboxInput")


@register.filter
def pairs(value):
    """'a|A,b|B' -> [('a', 'A'), ('b', 'B')] untuk pilihan tetap di template."""
    return [tuple(item.split("|", 1)) for item in str(value).split(",") if "|" in item]


@register.filter
def initials(name):
    """'Ani Wijaya' -> 'AW', 'budi' -> 'BU', kosong -> '?' (avatar tanpa foto)."""
    words = [w for w in str(name or "").replace("(", " ").replace(")", " ").split() if w[:1].isalnum()]
    if not words:
        return "?"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[-1][0]).upper()


@register.filter
def avatar_tone(name):
    """Warna avatar tetap per nama (6 nada lembut): av-0 … av-5."""
    return f"av-{sum(ord(c) for c in str(name or '')) % 6}"


@register.filter
def pct_of(value, total):
    """Persen bilangan bulat 0..100 untuk bilah progres (aman bila total kosong / nol)."""
    try:
        v, t = float(value), float(total)
    except (TypeError, ValueError):
        return 0
    if t <= 0:
        return 0
    return max(0, min(100, round(v * 100 / t)))
