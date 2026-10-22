#!/bin/sh
set -eu

if [ "${RUN_STARTUP_TASKS:-true}" = "true" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
fi

exec "$@"
