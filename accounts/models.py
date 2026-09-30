from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField("Email", unique=True)
    full_name = models.CharField("Nama lengkap", max_length=150)
    is_active = models.BooleanField("Aktif", default=False, help_text="Aktif setelah email diverifikasi.")
    is_staff = models.BooleanField(default=False)
    is_super_admin = models.BooleanField("Super admin (semua cabang)", default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]
    objects = UserManager()

    class Meta:
        verbose_name = "Pengguna"
        verbose_name_plural = "Pengguna"

    def save(self, *args, **kwargs):
        self.email = (self.email or "").strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return self.full_name or self.email
