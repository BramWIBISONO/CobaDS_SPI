"""Tulis docs/PERMISSIONS.md dari kode (izin bernama x peran) agar dokumentasi selalu sama dengan aturan server.
    .venv/Scripts/python manage.py permissions_doc"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core.capabilities import ROLE_LABELS
from core.permissions import PERMISSIONS, perms_for_role

ROLES = ["BRANCH_ADMIN", "MANAGER", "CSO", "FINANCE", "ACADEMIC", "TEACHER"]


def render_doc():
    lines = [
        "# Izin dan peran",
        "",
        "DIBANGKITKAN dari `core/permissions.py` + `core/capabilities.py` oleh `manage.py permissions_doc` - jangan diedit tangan.",
        "Setiap aksi dicek di server (`require_perm`); menyembunyikan tombol bukan pengaman.",
        "Super Admin memiliki semua izin di semua cabang. Staff = CSO, Management = Manager.",
        "",
        "| Izin | Kemampuan | " + " | ".join(ROLE_LABELS[r] for r in ROLES) + " |",
        "|---|---|" + "---|" * len(ROLES),
    ]
    by_role = {r: perms_for_role(r) for r in ROLES}
    for name, cap in PERMISSIONS.items():
        cells = ["✓" if name in by_role[r] else "–" for r in ROLES]
        lines.append(f"| `{name}` | {cap.value} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


class Command(BaseCommand):
    help = "Tulis docs/PERMISSIONS.md dari aturan izin di kode."

    def handle(self, *args, **opts):
        path = Path(settings.BASE_DIR) / "docs" / "PERMISSIONS.md"
        path.write_text(render_doc(), encoding="utf-8")
        self.stdout.write(f"tulis {path}")
