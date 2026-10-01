from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import email_verification_token


def _send(template, user, context):
    subject = render_to_string(f"accounts/email/{template}_subject.txt", context).strip()
    body = render_to_string(f"accounts/email/{template}_body.txt", context)
    send_mail(subject, body, None, [user.email])


def send_verification(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    url = request.build_absolute_uri(reverse("accounts:verify", args=[uid, email_verification_token.make_token(user)]))
    _send("verify", user, {"user": user, "url": url})


def send_already_registered(request, user):
    _send("registered", user, {"user": user, "login_url": request.build_absolute_uri(reverse("accounts:login")),
                                "reset_url": request.build_absolute_uri(reverse("accounts:password_reset"))})
