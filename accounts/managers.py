from django.contrib.auth.base_user import BaseUserManager
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email wajib diisi")
        user = self.model(email=self.normalize_email(email).strip().lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_active", True)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_super_admin", True)
        extra.setdefault("email_verified_at", timezone.now())
        return self.create_user(email, password, **extra)

    def get_by_natural_key(self, email):
        return self.get(email__iexact=email)
