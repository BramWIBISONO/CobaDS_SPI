from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from branches.models import Membership

from .models import User


class GrantAccessForm(forms.Form):
    email = forms.EmailField(label="Email pengguna")
    role = forms.ChoiceField(label="Peran", choices=Membership.ROLE_CHOICES)
    teacher_name = forms.CharField(label="Nama guru (untuk peran Teacher)", required=False, max_length=100,
                                   help_text="Nama seperti di jadwal & sesi, mis. Mr. Tryo")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is None:
            raise ValidationError("Tidak ada pengguna aktif (email terverifikasi) dengan email ini.")
        self.user = user
        return email

    def clean(self):
        data = super().clean()
        if data.get("role") == "TEACHER" and not data.get("teacher_name"):
            self.add_error("teacher_name", "Isi nama guru seperti di jadwal.")
        return data


class LoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Password", strip=False, widget=forms.PasswordInput)


class SignupForm(forms.Form):
    full_name = forms.CharField(label="Nama lengkap", max_length=150)
    email = forms.EmailField(label="Email")
    password1 = forms.CharField(label="Password", strip=False, widget=forms.PasswordInput,
                                help_text="Minimal 10 karakter, tidak mirip nama / email, tidak umum.")
    password2 = forms.CharField(label="Ulangi password", strip=False, widget=forms.PasswordInput)

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean(self):
        data = super().clean()
        p1, p2 = data.get("password1"), data.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Password tidak sama.")
        elif p1:
            try:
                validate_password(p1, user=User(email=data.get("email", ""), full_name=data.get("full_name", "")))
            except ValidationError as exc:
                self.add_error("password1", exc)
        return data


class ResendForm(forms.Form):
    email = forms.EmailField(label="Email")
