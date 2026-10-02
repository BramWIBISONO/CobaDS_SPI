from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"
    verbose_name = "Akun"

    def ready(self):
        from . import checks  # noqa: F401  (mendaftarkan pemeriksaan sistem)
