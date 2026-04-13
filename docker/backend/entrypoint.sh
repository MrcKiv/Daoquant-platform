#!/bin/sh
set -eu

python - <<'PY'
import os
import socket
import time

host = os.getenv("DB_HOST", "db")
port = int(os.getenv("DB_PORT", "3306"))

for attempt in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f"Database is reachable at {host}:{port}")
            break
    except OSError:
        time.sleep(2)
else:
    raise SystemExit(f"Database is not reachable at {host}:{port}")
PY

if [ "${DJANGO_AUTO_MIGRATE:-1}" = "1" ]; then
  python manage.py migrate --noinput
else
  echo "Skipping Django migrations because DJANGO_AUTO_MIGRATE=${DJANGO_AUTO_MIGRATE:-0}"
fi

python manage.py collectstatic --noinput

exec gunicorn backend.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-120}"
