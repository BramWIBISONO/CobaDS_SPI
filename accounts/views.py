from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode
from django.views.decorators.http import require_POST

from . import demo, ratelimit
from .emails import send_already_registered, send_verification
from .forms import LoginForm, ResendForm, SignupForm
from .models import User
from .tokens import email_verification_token


def _client_ip(request):
    return request.META.get("REMOTE_ADDR", "")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:home")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email, password, ip = form.cleaned_data["email"].lower(), form.cleaned_data["password"], _client_ip(request)
        if ratelimit.is_blocked(email, ip):
            form.add_error(None, "Terlalu banyak percobaan gagal. Coba lagi dalam 15 menit.")
        else:
            user = authenticate(request, username=email, password=password)
            if user is None:
                ratelimit.register_failure(email, ip)
                pending = User.objects.filter(email__iexact=email, is_active=False, email_verified_at__isnull=True).first()
                if pending is not None and pending.check_password(password):
                    form.add_error(None, "Email belum diverifikasi. Buka tautan di email Anda atau kirim ulang tautan verifikasi.")
                else:
                    form.add_error(None, "Email atau password salah.")
            else:
                ratelimit.reset(email, ip)
                login(request, user)
                nxt = request.GET.get("next", "")
                if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}, request.is_secure()):
                    return redirect(nxt)
                return redirect("core:home")
    return render(request, "accounts/login.html", {"form": form, "demo_users": demo.available() if demo.demo_enabled() else []})


def signup_view(request):
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        existing = User.objects.filter(email__iexact=email).first()
        if existing is not None:
            send_already_registered(request, existing)
        else:
            user = User.objects.create_user(email, form.cleaned_data["password1"], full_name=form.cleaned_data["full_name"])
            send_verification(request, user)
        return redirect("accounts:signup_done")
    return render(request, "accounts/signup.html", {"form": form})


def signup_done_view(request):
    return render(request, "accounts/signup_done.html")


def verify_view(request, uidb64, token):
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None
    if user is not None and not user.is_active and email_verification_token.check_token(user, token):
        user.is_active = True
        user.email_verified_at = timezone.now()
        user.save(update_fields=["is_active", "email_verified_at"])
        messages.success(request, "Email terverifikasi. Silakan masuk. Akses cabang diberikan oleh Branch Admin.")
        return redirect("accounts:login")
    return render(request, "accounts/verify_failed.html", status=400)


def resend_view(request):
    form = ResendForm(request.POST or None)
    sent = False
    if request.method == "POST" and form.is_valid():
        user = User.objects.filter(email__iexact=form.cleaned_data["email"], is_active=False, email_verified_at__isnull=True).first()
        if user is not None:
            send_verification(request, user)
        sent = True                                   # jawaban sama untuk email apa pun
    return render(request, "accounts/resend.html", {"form": form, "sent": sent})


@require_POST
def demo_login_view(request):
    """Masuk satu klik untuk akun demo - hanya DEBUG & DEMO_ACCOUNTS, hanya email daftar demo."""
    email = request.POST.get("email", "").strip().lower()
    if not demo.demo_enabled() or email not in demo.DEMO_EMAILS:
        raise Http404
    user = User.objects.filter(email=email, is_active=True).first()
    if user is None:
        raise Http404
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return redirect("core:home")
