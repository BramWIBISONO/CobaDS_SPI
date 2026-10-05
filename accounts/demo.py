"""Akun demo per peran untuk mencoba aplikasi di laptop (spesifikasi dasbor gelombang 1 §5). Hanya bila DEBUG & DEMO_ACCOUNTS.
Kata sandi bersama disimpan di .env (DEMO_PASSWORD) - tidak pernah ditampilkan di halaman."""
import re
import secrets

from django.conf import settings
from django.utils import timezone

from accounts.models import User
from branches.models import Branch, Membership
from masterdata.models import TeacherMaster

DEMO_USERS = [
    {"email": "superadmin@spi.local", "name": "Demo Super Admin", "branch": None, "role": "SUPER_ADMIN"},
    {"email": "admin.jkt@spi.local", "name": "Demo Admin Jakarta", "branch": "SPI-JKT", "role": "BRANCH_ADMIN"},
    {"email": "manager.jkt@spi.local", "name": "Demo Manager Jakarta", "branch": "SPI-JKT", "role": "MANAGER"},
    {"email": "cso.jkt@spi.local", "name": "Demo CSO Jakarta", "branch": "SPI-JKT", "role": "CSO"},
    {"email": "finance.jkt@spi.local", "name": "Demo Finance Jakarta", "branch": "SPI-JKT", "role": "FINANCE"},
    {"email": "academic.jkt@spi.local", "name": "Demo Academic Jakarta", "branch": "SPI-JKT", "role": "ACADEMIC"},
    {"email": "guru.jkt@spi.local", "name": "Demo Guru Jakarta", "branch": "SPI-JKT", "role": "TEACHER"},
    {"email": "admin.as@spi.local", "name": "Demo Admin Alam Sutera", "branch": "SPI-AS", "role": "BRANCH_ADMIN"},
]
DEMO_EMAILS = {u["email"] for u in DEMO_USERS}
ROLE_TEXT = {"SUPER_ADMIN": "Super Admin", "BRANCH_ADMIN": "Branch Admin", "MANAGER": "Manager", "CSO": "CSO", "FINANCE": "Finance",
             "ACADEMIC": "Academic", "TEACHER": "Teacher"}


def demo_enabled():
    return bool(settings.DEBUG and getattr(settings, "DEMO_ACCOUNTS", False))


def ensure_password(env_file):
    """DEMO_PASSWORD dari .env; bila kosong dibuat acak sekali dan ditulis ke .env."""
    text = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
    m = re.search(r"^DEMO_PASSWORD=(.+)$", text, re.M)
    if m and m.group(1).strip():
        return m.group(1).strip()
    if getattr(settings, "DEMO_PASSWORD", ""):
        password = settings.DEMO_PASSWORD
    else:
        password = secrets.token_urlsafe(18)
    line = f"DEMO_PASSWORD={password}"
    text = re.sub(r"^DEMO_PASSWORD=.*$", line, text, flags=re.M) if m else (text.rstrip("\n") + "\n" + line + "\n").lstrip("\n")
    env_file.write_text(text, encoding="utf-8")
    return password


def seed(password):
    now, out = timezone.now(), []
    branches = {b.code: b for b in Branch.objects.filter(code__in={u["branch"] for u in DEMO_USERS if u["branch"]})}
    for spec in DEMO_USERS:
        branch = branches.get(spec["branch"]) if spec["branch"] else None
        if spec["branch"] and branch is None:
            out.append({**spec, "status": f"dilewati: cabang {spec['branch']} belum ada"})
            continue
        user = User.objects.filter(email=spec["email"]).first() or User(email=spec["email"])
        user.full_name, user.is_active, user.is_super_admin = spec["name"], True, spec["role"] == "SUPER_ADMIN"
        user.email_verified_at = user.email_verified_at or now
        user.set_password(password)
        user.save()
        if branch is not None:
            teacher = ""
            if spec["role"] == "TEACHER":
                teacher = demo_teacher_name(branch)
            Membership.objects.update_or_create(user=user, branch=branch, defaults={"role": spec["role"], "teacher_name": teacher})
        out.append({**spec, "status": "siap"})
    return out


def demo_teacher_name(branch):
    """Guru aktif yang punya jadwal resmi (agar Jadwal Saya demo berisi); bila tidak ada: guru pertama di daftar."""
    from classes.models import ClassSchedule
    from masterdata.services import teacher_key

    teachers = list(TeacherMaster.objects.for_branch(branch).exclude(name="").order_by("row_no"))
    scheduled = {teacher_key(t) for t in ClassSchedule.objects.for_branch(branch).values_list("teacher", flat=True)}
    best = next((t for t in teachers if t.status.upper() == "ACTIVE" and teacher_key(t.name) in scheduled), None)
    best = best or (teachers[0] if teachers else None)
    return best.name if best else "Guru Demo"


def available():
    """Akun demo yang ada & aktif, untuk panel di halaman Masuk."""
    have = set(User.objects.filter(email__in=DEMO_EMAILS, is_active=True).values_list("email", flat=True))
    return [{**u, "role_text": ROLE_TEXT[u["role"]]} for u in DEMO_USERS if u["email"] in have]
