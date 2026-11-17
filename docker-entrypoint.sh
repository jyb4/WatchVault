#!/bin/sh
set -eu

if [ "${DJANGO_ENV:-development}" = "production" ]; then
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
fi

exec "$@"
