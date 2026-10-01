from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Tautan verifikasi email: berlaku PASSWORD_RESET_TIMEOUT, hanya sekali (berubah begitu akun aktif)."""
    key_salt = "spi_web.accounts.EmailVerificationTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.email}{user.is_active}{user.email_verified_at}{timestamp}"


email_verification_token = EmailVerificationTokenGenerator()
