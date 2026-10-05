from django.apps import AppConfig


class AuditConfig(AppConfig):
    name = "audit"
    verbose_name = "Audit"

    def ready(self):
        from . import signals  # noqa: F401  (masuk / keluar / gagal masuk)
