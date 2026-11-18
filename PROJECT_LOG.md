# WatchVault — living project log

This is the chronological record of progress, decisions, and next work. Update it at the end of each meaningful work session. For the authoritative current architecture and operating procedures, use [the canonical documentation](docs/CANONICAL.md).

## Project snapshot

- **Project:** WatchVault
- **Purpose:** A self-hosted, multi-user TV-show discovery CMS with personal watchlists and a future catalog-grounded AI Guide.
- **Primary stack:** Django, PostgreSQL, pgvector, Docker Compose; Neo4j is an optional later graph-service profile.
- **Catalog source:** [TVmaze API](https://www.tvmaze.com/api)
- **Production address:** `jybdeployment.com` (replaces the existing placeholder container behind the active Caddy route)
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
| 3. Catalog CMS | Show/genre models, editorial statuses, Django Admin | In progress — deployed catalog is live |
| 4. TVmaze import | Search-by-title import command, validation, attribution | In progress — live catalog seeded with a published show |
| 5. Member experience | Responsive design, registration, add/remove watchlist, filters | In progress — cinematic discovery UI and expanded catalog search deployed |
| 6. Semantic retrieval | Chunking, embeddings, pgvector search | Not started |
| 7. Graph discovery | People/show/genre relationship graph and related shows | Not started |
| 8. RAG AI Guide | Source-linked, catalog-only answers | Not started |
| 9. Operations | Automated tests, GitHub Actions, server deployment, HTTPS, backups, analytics | In progress — live deployment verified through Caddy HTTPS |

## Current implementation

- The public app has starter routes for Home, Discover, Show Detail, Sign In, and My Watchlist.
- Django Admin supports editorial management of shows and genres.
- A `Show` contains a TVmaze ID and source URL, import timestamp, genres, synopsis, image URL, premiere date, network, rating, and publishing status.
- `python manage.py import_tvmaze "Show Name"` imports the closest TVmaze search result as a **draft**.
- The importer handles empty searches, network errors, HTTP failures, and rate limiting. It does not store an API key because the public TVmaze endpoints used here do not require one.
- The project now has a production Compose configuration, Caddy HTTPS reverse proxy, environment template, deployment runbook, and GitHub Actions test workflow.
- WatchVault replaced the prior placeholder container on `jybdeployment.com` after a separate port-8090 staging check. The stopped `jyb-prod` container is retained on the server as a rollback option.
- The redesigned discovery experience was staged, tested, and promoted with 18 published TVmaze shows and catalog search across titles, genres, networks, and descriptions.
- The QA dashboard now uses an original app-style discovery layout: responsive desktop/sidebar and mobile navigation, an editorial featured carousel, dynamic trending/recently-added rails, and a visual personal watchlist.

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
8. Deploy to port 8090 and verify locally on the server before switching WatchVault to the active port 8080.

## Evidence and verification

| Check | Result | Notes |
| --- | --- | --- |
| Docker Compose configuration | Passed | Development configuration parses successfully. |
| Django runtime/test suite | Pending | Docker Desktop was not running during initial setup. |
| Docker Desktop runtime | Blocked | Docker Desktop opened with a local startup error; no reset was performed. |
| Docker Desktop access | Blocked | Docker Desktop is now running, but the current Windows account is denied access to its Docker engine pipe. |
| TVmaze API documentation reviewed | Complete | Search, detail, images, caching, rate-limit, and license rules reviewed. |
| Live production homepage | Passed | `https://jybdeployment.com` returns 200 through Caddy and renders WatchVault with a published TVmaze show. |
| Live production stylesheet | Passed | The hashed WatchVault stylesheet returns 200 and is cacheable. |
| Redesign and catalog search release | Passed | Private staging test suite passed 3/3; the public homepage and `science` search both returned the new catalog. |
