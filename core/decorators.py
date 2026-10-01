from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


def require_cap(cap):
    """Halaman cabang: login, cabang aktif, dan kemampuan `cap` untuk peran pengguna di cabang itu (dicek di server)."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(request, *args, **kwargs):
            if request.branch is None:
                return redirect("core:home")
            if cap not in request.caps:
                return render(request, "core/forbidden.html", status=403)
            return view(request, *args, **kwargs)
        return wrapped
    return decorator
