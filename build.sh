#!/usr/bin/env bash

set -o errexit

echo "========================================"
echo "SPI SUPER APP BUILD"
echo "========================================"

pip install -r requirements.txt

python manage.py collectstatic --no-input

python manage.py migrate

echo "BUILD COMPLETED"
