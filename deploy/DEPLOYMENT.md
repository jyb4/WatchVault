# WatchVault deployment guide

This guide prepares WatchVault for the existing `jybdeployment.com` Ubuntu server. Caddy already owns ports 80/443, handles HTTPS, and forwards `jybdeployment.com` to port 8080. WatchVault replaces the container behind that route; it does **not** start another reverse proxy or modify Caddy.

## Before deployment

1. Install Docker Engine and Docker Compose on the server.
2. Clone the WatchVault repository onto the server.
3. Copy `.env.production.example` to `.env.production` and replace every example secret.

Never commit `.env.production`. It contains the database password and Django secret key.

## First deployment

From the project directory on the server, use port 8090 first to verify the new release without affecting the placeholder:

```text
HOSTED_PORT=8090 docker compose -f compose.production.yaml up --build --detach
curl -I http://127.0.0.1:8090
```

After successful verification, stop the placeholder container, restart WatchVault with `HOSTED_PORT=8080`, then open `https://jybdeployment.com/`. The old container should remain stopped as a quick rollback option.

## Updating

```text
git pull
docker compose -f compose.production.yaml up --build --detach
```

## Operations checklist

- Back up the `postgres_data` volume before upgrades and test restoring it.
- Review `docker compose -f compose.production.yaml logs --follow` after deployment.
- Keep the host operating system, Docker images, and Python dependencies updated.
- Set `DJANGO_DEBUG=False` and use a unique `DJANGO_SECRET_KEY` and database password.
- Do not expose PostgreSQL ports publicly.
- Add server monitoring and a scheduled backup before inviting users.

## QA daily TVmaze refresh

QA uses the `deploy` account's cron schedule to refresh the searchable TVmaze catalog every morning at 6:00 AM America/New_York. It runs the bounded `sync_tvmaze_schedule --days 7 --limit 36` command inside the QA container. The task only imports or updates catalog records; it does not change the editorial hero, Trending, or pinned Fresh choices.

The versioned runner is `deploy/cron/watchvault-qa-tvmaze-sync.sh`. Install it once after pulling a release:

```text
chmod 755 deploy/cron/watchvault-qa-tvmaze-sync.sh
mkdir -p logs
crontab deploy/cron/watchvault-qa-tvmaze-sync.crontab
```

Check the schedule and most recent result with:

```text
crontab -l
tail -n 100 logs/tvmaze-sync.log
```

## Local testing

Start Docker Desktop, then use the development configuration:

```text
docker compose up --build --detach
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py import_tvmaze "The Bear"
```

Visit `http://localhost:8000`. Publish imported drafts in `/admin/` before they appear in the public catalog.
