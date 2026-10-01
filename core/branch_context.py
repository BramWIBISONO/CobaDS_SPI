"""Cabang aktif per sesi: hanya cabang tempat pengguna punya peran (SUPER_ADMIN: semua)."""
from branches.models import Branch

from .capabilities import ROLE_LABELS, caps_for, role_of
from .nav import nav_for

SESSION_KEY = "spi_branch_id"


def allowed_branches(user):
    if not getattr(user, "is_authenticated", False):
        return Branch.objects.none()
    if user.is_super_admin:
        return Branch.objects.all()
    return Branch.objects.filter(memberships__user=user).distinct()


def _session_branch(allowed, session):
    try:
        pk = int(session.get(SESSION_KEY))
    except (TypeError, ValueError):
        return None
    return allowed.filter(pk=pk).first()


class BranchContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.branch, request.role, request.caps = None, None, frozenset()
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            allowed = allowed_branches(user)
            branch = _session_branch(allowed, request.session)
            if branch is None:
                request.session.pop(SESSION_KEY, None)
                if allowed.count() == 1:
                    branch = allowed.first()
                    request.session[SESSION_KEY] = branch.pk
            request.branch = branch
            request.role = role_of(user, branch)
            request.caps = caps_for(user, branch)
        return self.get_response(request)


def branch_context(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {"current_branch": getattr(request, "branch", None), "allowed_branches": list(allowed_branches(user)),
            "role": getattr(request, "role", None), "role_label": ROLE_LABELS.get(getattr(request, "role", None), ""),
            "caps": getattr(request, "caps", frozenset()), "nav": nav_for(request)}
