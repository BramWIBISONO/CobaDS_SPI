#!/usr/bin/env bash
# Setiap kali Codespace dibuka: perbarui akun demo lalu jalankan server di port 8000.
cd "$(dirname "$0")/.."
python manage.py migrate --no-input >/dev/null
python manage.py seed_demo_accounts >/dev/null 2>&1 || true

URL="http://localhost:8000"
if [ -n "${CODESPACE_NAME:-}" ]; then
  URL="https://${CODESPACE_NAME}-8000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
fi
echo ""
echo "============================================================"
echo " SPI Super App: $URL"
echo " Masuk sebagai : superadmin@spi.local"
echo " Kata sandi    : $(grep '^DEMO_PASSWORD=' .env | cut -d= -f2-)"
echo " (Data masih kosong: menu Cabang -> buat cabang, lalu Impor Data -> unggah workbook Excel)"
echo "============================================================"
echo ""
python manage.py runserver 0.0.0.0:8000
