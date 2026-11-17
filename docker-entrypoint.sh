#!/bin/sh
set -eu

if [ "${DJANGO_ENV:-development}" = "production" ]; then
  python manage.py collectstatic --noinput
fi

exec "$@"
