from django import forms
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
