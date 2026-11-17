# WatchVault — living project log

This document is the project’s single source of truth for progress, decisions, and next work. Update it at the end of each meaningful work session.

## Project snapshot

- **Project:** WatchVault
- **Purpose:** A self-hosted, multi-user TV-show discovery CMS with personal watchlists and a future catalog-grounded AI Guide.
- **Primary stack:** Django, PostgreSQL, pgvector, Docker Compose; Neo4j is an optional later graph-service profile.
- **Catalog source:** [TVmaze API](https://www.tvmaze.com/api)
- **Planned production address:** `watchvault.jybdeployment.com` (keeps the existing root-domain site online)
- **Original prototype:** PHP project retained outside this folder for reference only.

## Product decisions

| Decision | Why it was made | Status |
| --- | --- | --- |
| TV shows only | Keeps the first release focused; matches the selected API. | Confirmed |
| Django rebuild | Demonstrates CMS, roles, admin workflows, and maintainable server-side design. | Confirmed |
| Import to local catalog | Gives editors control and prevents a live API dependency on every page view. | Confirmed |
| Imported content begins as a draft | Supports editorial review, data quality, and responsible publishing. | Confirmed |
| TVmaze attribution | The API’s CC BY-SA license requires attribution and ShareAlike compliance. | Confirmed |
| Vector search before graph features | Semantic retrieval is the direct foundation for RAG; graph work follows a stable catalog. | Confirmed |

## Milestones

| Milestone | Deliverable | Status |
| --- | --- | --- |
| 1. Strategy and information architecture | Project brief, roles, sitemap, user journeys | Complete |
| 2. Development foundation | Django structure, Docker Compose, PostgreSQL/pgvector, Git repository | Complete; Docker Desktop has a startup error, so runtime verification is blocked locally |
| 3. Catalog CMS | Show/genre models, editorial statuses, Django Admin | In progress |
| 4. TVmaze import | Search-by-title import command, validation, attribution | In progress |
| 5. Member experience | Responsive design, registration, add/remove watchlist, filters | In progress — responsive UI and watchlist mutations added |
| 6. Semantic retrieval | Chunking, embeddings, pgvector search | Not started |
| 7. Graph discovery | People/show/genre relationship graph and related shows | Not started |
| 8. RAG AI Guide | Source-linked, catalog-only answers | Not started |
| 9. Operations | Automated tests, GitHub Actions, server deployment, HTTPS, backups, analytics | In progress — CI and Docker/Caddy deployment configuration added |

## Current implementation

- The public app has starter routes for Home, Discover, Show Detail, Sign In, and My Watchlist.
- Django Admin supports editorial management of shows and genres.
- A `Show` contains a TVmaze ID and source URL, import timestamp, genres, synopsis, image URL, premiere date, network, rating, and publishing status.
- `python manage.py import_tvmaze "Show Name"` imports the closest TVmaze search result as a **draft**.
- The importer handles empty searches, network errors, HTTP failures, and rate limiting. It does not store an API key because the public TVmaze endpoints used here do not require one.
- The project now has a production Compose configuration, Caddy HTTPS reverse proxy, environment template, deployment runbook, and GitHub Actions test workflow.

## TVmaze integration rules

1. Import selected shows rather than mirror the complete TVmaze catalog.
2. Preserve the TVmaze show ID and source link for every imported entry.
3. Keep the visible TVmaze attribution in the application footer.
4. Use a recognizable User-Agent, back off after HTTP 429, and respect the documented request rate.
5. Review image and data licensing before production deployment; do not copy third-party review content without permission.

## Next work session

1. Start Docker Desktop.
2. Run `docker compose up --build --detach` from the WatchVault folder.
3. Run `docker compose exec web python manage.py migrate`.
4. Create an administrator account.
5. Import and review a small set of TV shows in Django Admin.
6. Add account registration and catalog filters.
7. Before server deployment, copy `.env.production.example` to `.env.production` on the server and replace its example secrets.
8. Create the `watchvault.jybdeployment.com` DNS record before deploying; do not replace the active root-domain site without a deliberate migration plan.

## Evidence and verification

| Check | Result | Notes |
| --- | --- | --- |
| Docker Compose configuration | Passed | Development configuration parses successfully. |
| Django runtime/test suite | Pending | Docker Desktop was not running during initial setup. |
| Docker Desktop runtime | Blocked | Docker Desktop opened with a local startup error; no reset was performed. |
| Docker Desktop access | Blocked | Docker Desktop is now running, but the current Windows account is denied access to its Docker engine pipe. |
| TVmaze API documentation reviewed | Complete | Search, detail, images, caching, rate-limit, and license rules reviewed. |
