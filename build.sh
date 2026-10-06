#!/usr/bin/env bash
# Dijalankan server hosting (Render) setiap deploy.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py createcachetable

# Super admin pertama dari DJANGO_SUPERUSER_EMAIL / _PASSWORD / _FULL_NAME (dilewati bila belum diisi atau sudah ada)
if [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  python manage.py createsuperuser --no-input || echo "Super admin ${DJANGO_SUPERUSER_EMAIL} sudah ada - dilewati."
fi
