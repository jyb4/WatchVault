#!/bin/sh
set -eu

cd /home/deploy/WatchVault
exec /usr/bin/sudo -n /usr/bin/docker compose \
  --env-file /home/deploy/WatchVault/.env.staging \
  -f /home/deploy/WatchVault/compose.production.yaml \
  --project-name watchvault-staging \
  exec -T web python manage.py sync_tvmaze_schedule --days 7 --limit 36
