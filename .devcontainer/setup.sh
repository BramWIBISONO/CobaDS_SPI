#!/usr/bin/env bash
# Sekali saat Codespace dibuat: pasang paket, buat .env, siapkan database, akun demo.
set -o errexit
cd "$(dirname "$0")/.."

pip install --disable-pip-version-check -q -r requirements.txt

if [ ! -f .env ]; then
  cat > .env <<ENV
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(50))')
DEBUG=True
DATABASE_URL=postgres://postgres:postgres@localhost:5432/spi_web
ALLOWED_HOSTS=localhost,127.0.0.1,.app.github.dev
CSRF_TRUSTED_ORIGINS=https://*.app.github.dev
DEMO_ACCOUNTS=True
DEMO_PASSWORD=$(python -c 'import secrets; print(secrets.token_urlsafe(12))')
ENV
fi

echo "Menunggu PostgreSQL..."
for _ in $(seq 1 30); do
  python -c "import psycopg; psycopg.connect('postgres://postgres:postgres@localhost:5432/spi_web').close()" 2>/dev/null && break
  sleep 2
done

python manage.py migrate --no-input
python manage.py createcachetable
python manage.py seed_demo_accounts
