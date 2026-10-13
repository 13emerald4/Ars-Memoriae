# Built from the repository root (docker-compose sets `context: .`) so the
# frontend bundle can be compiled here and served by the API on one origin.

FROM node:24-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim

ARG INSTALL_FSRS_OPTIMIZER=0

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MEDIA_ROOT=/data/media

WORKDIR /srv

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
 && rm -rf /var/lib/apt/lists/*

# Code practice runs TypeScript/JavaScript through Node. 24+ strips TS types
# natively, which the TS worker relies on; Debian's packaged node is too old.
COPY --from=node:24-slim /usr/local/bin/node /usr/local/bin/node

COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --no-cache-dir . \
 && if [ "$INSTALL_FSRS_OPTIMIZER" = "1" ]; then pip install --no-cache-dir ".[optimizer]"; fi

COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY backend/entrypoint.sh ./
# app/main.py looks for the bundle at <repo>/frontend/dist, i.e. /frontend/dist here.
COPY --from=frontend /build/dist /frontend/dist

# Code practice runs user code as whatever user the API runs as, so the API
# must not be root. The entrypoint starts as root only to fix ownership of
# volumes created by older images, then drops to this user.
RUN chmod +x entrypoint.sh \
 && useradd --create-home --uid 10001 app \
 && mkdir -p /data/media \
 && chown -R app:app /srv /data/media

EXPOSE 8000
CMD ["./entrypoint.sh"]
