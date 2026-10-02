from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security)
def demo_accounts_check(app_configs, **kwargs):
    if getattr(settings, "DEMO_ACCOUNTS", False) and not settings.DEBUG:
        return [Error("DEMO_ACCOUNTS hanya boleh aktif bila DEBUG=True (akun demo memakai satu kata sandi bersama).",
                      hint="Hapus DEMO_ACCOUNTS dari .env server.", id="spi.E001")]
    return []
