# WatchVault deployment guide

This guide prepares WatchVault for a Linux server with Docker Engine, Docker Compose, a domain name, and ports 80/443 reachable from the internet. Caddy obtains and renews HTTPS certificates automatically when the domain DNS points to the server.

## Before deployment

1. Install Docker Engine and Docker Compose on the server.
2. Point a domain or subdomain, such as `watchvault.example.com`, to the server’s public IP address.
3. Allow inbound TCP ports 80 and 443 through the server firewall and hosting provider firewall.
4. Clone the WatchVault repository onto the server.
5. Copy `.env.production.example` to `.env.production` and replace every example secret and domain.

Never commit `.env.production`. It contains the database password and Django secret key.

## First deployment

From the project directory on the server:

```text
docker compose -f compose.production.yaml up --build --detach
docker compose -f compose.production.yaml exec web python manage.py migrate
docker compose -f compose.production.yaml exec web python manage.py createsuperuser
```

Open `https://YOUR-DOMAIN/admin/`, create an editor account, import a small catalog, review the drafts, and publish only approved entries.

## Updating

```text
git pull
docker compose -f compose.production.yaml up --build --detach
docker compose -f compose.production.yaml exec web python manage.py migrate
```

## Operations checklist

- Back up the `postgres_data` volume before upgrades and test restoring it.
- Review `docker compose -f compose.production.yaml logs --follow` after deployment.
- Keep the host operating system, Docker images, and Python dependencies updated.
- Set `DJANGO_DEBUG=False` and use a unique `DJANGO_SECRET_KEY` and database password.
- Do not expose PostgreSQL or Neo4j ports publicly.
- Add server monitoring and a scheduled backup before inviting users.

## Local testing

Start Docker Desktop, then use the development configuration:

```text
docker compose up --build --detach
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py import_tvmaze "The Bear"
```

Visit `http://localhost:8000`. Publish imported drafts in `/admin/` before they appear in the public catalog.
