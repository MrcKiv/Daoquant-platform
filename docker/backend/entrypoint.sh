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

python - <<'PY'
import os

import pymysql

tables = (
    "auth_group",
    "auth_group_permissions",
    "auth_permission",
    "auth_user",
    "auth_user_groups",
    "auth_user_user_permissions",
    "django_admin_log",
    "django_content_type",
)

conn = pymysql.connect(
    host=os.getenv("DB_HOST", "db"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", "123456"),
    database=os.getenv("DB_NAME", "jdgp"),
    charset=os.getenv("DB_CHARSET", "utf8mb4"),
)

try:
    with conn.cursor() as cursor:
        placeholders = ", ".join(["%s"] * len(tables))
        cursor.execute(
            f"""
            SELECT TABLE_NAME, COLUMN_TYPE, EXTRA, COLUMN_KEY
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND COLUMN_NAME = 'id'
              AND TABLE_NAME IN ({placeholders})
            ORDER BY TABLE_NAME
            """,
            tables,
        )
        repairs = []
        for table_name, column_type, extra, column_key in cursor.fetchall():
            if "auto_increment" in (extra or "").lower():
                continue
            if table_name == "django_admin_log" and column_key != "PRI":
                cursor.execute("SET @next_id := 0")
                cursor.execute(
                    """
                    UPDATE `django_admin_log`
                    SET id = (@next_id := @next_id + 1)
                    ORDER BY COALESCE(id, 0), action_time, user_id, content_type_id
                    """
                )
                cursor.execute(
                    f"ALTER TABLE `{table_name}` MODIFY COLUMN `id` {column_type} NOT NULL"
                )
                cursor.execute(f"ALTER TABLE `{table_name}` ADD PRIMARY KEY (`id`)")
            cursor.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM `{table_name}`")
            next_id = max(int(cursor.fetchone()[0]), 1)
            cursor.execute(
                f"ALTER TABLE `{table_name}` MODIFY COLUMN `id` {column_type} NOT NULL AUTO_INCREMENT"
            )
            cursor.execute(f"ALTER TABLE `{table_name}` AUTO_INCREMENT = {next_id}")
            repairs.append((table_name, next_id))
    conn.commit()
finally:
    conn.close()

if repairs:
    for table_name, next_id in repairs:
        print(f"Normalized AUTO_INCREMENT for {table_name}.id (next={next_id})")
else:
    print("Django system table ids already use AUTO_INCREMENT")
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
  --timeout "${GUNICORN_TIMEOUT:-1800}"
