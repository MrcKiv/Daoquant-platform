FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-web.txt /app/requirements-web.txt

RUN pip install --upgrade pip \
    && pip install -r /app/requirements-web.txt

COPY backend_main /app/backend_main
COPY docker/backend/entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

WORKDIR /app/backend_main

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
