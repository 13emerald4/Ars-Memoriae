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

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir . \
 && if [ "$INSTALL_FSRS_OPTIMIZER" = "1" ]; then pip install --no-cache-dir ".[optimizer]"; fi

COPY alembic.ini ./
COPY alembic ./alembic
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh && mkdir -p /data/media

EXPOSE 8000
CMD ["./entrypoint.sh"]
