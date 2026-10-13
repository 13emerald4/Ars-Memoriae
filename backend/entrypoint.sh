#!/bin/sh
set -e
# Started as root only to hand the media volume (possibly created by an older,
# root-run image) to the app user, then re-exec unprivileged: code practice
# runs user code as whatever user this process is.
if [ "$(id -u)" = "0" ]; then
  chown -R app:app /data/media
  exec setpriv --reuid=app --regid=app --init-groups "$0" "$@"
fi
echo "[entrypoint] running migrations…"
alembic upgrade head
echo "[entrypoint] starting API on :8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
