# WatchVault

WatchVault is a self-hosted TV-show discovery platform. Editors curate an approved TV catalog, members save shows to personal watchlists, and a future AI Guide will make recommendations grounded in that catalog.

## Current foundation

- Django CMS with an admin dashboard
- PostgreSQL with `pgvector` ready for future semantic search
- Docker Compose development environment
- Public home, show catalog, show-detail, authentication, and watchlist routes
- Editorial publishing workflow (`draft` → `published`)
- A provider-agnostic TV API import seam (the provider will be selected before implementation)

## Run locally

1. Copy `.env.example` to `.env` and change the development values.
2. Run `docker compose up --build`.
3. In another terminal, run `docker compose exec web python manage.py migrate`.
4. Create an administrator with `docker compose exec web python manage.py createsuperuser`.
5. Open `http://localhost:8000` and `/admin/`.

## Import a show from TVmaze

WatchVault uses [TVmaze's REST API](https://www.tvmaze.com/api) as its TV-only catalog source. After starting the containers and applying migrations, import one show at a time as an editorial **draft**:

```text
docker compose exec web python manage.py import_tvmaze "The Bear"
```

Review the imported profile in Django Admin and publish it only when it is ready. TVmaze allows free use with attribution and ShareAlike requirements; WatchVault keeps the TVmaze source URL and displays site attribution.

## Documentation

- [Project brief](docs/project-brief.md)
- [Information architecture](docs/information-architecture.md)
- [Architecture and delivery plan](docs/architecture.md)
- [Living project log](PROJECT_LOG.md)

## Original project

The PHP files in the parent folder are retained as the original course-project prototype. New work belongs in this `watchvault/` application.
