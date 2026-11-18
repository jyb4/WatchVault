# WatchVault canonical documentation

**Last updated:** 2026-11-17  
**Live site:** [https://jybdeployment.com](https://jybdeployment.com)  
**Source repository:** [github.com/jyb4/WatchVault](https://github.com/jyb4/WatchVault)

This is the authoritative technical and operational reference for WatchVault. Update this document whenever the deployed architecture, data model, security posture, or release process changes.

## 1. Product

WatchVault is a self-hosted TV-show discovery platform. It gives visitors a curated catalog of television shows, lets members maintain personal watchlists, and is designed to later support semantic discovery, graph relationships, and a source-linked RAG assistant.

The project intentionally focuses on TV shows only. Books and movies are not part of the current release.

## 2. Users and roles

| Role | What they can do |
| --- | --- |
| Visitor | Browse and search published shows. |
| Member | Browse published shows and maintain a personal watchlist. |
| Editor | Import, review, edit, and publish TV-show entries through Django Admin. |
| Administrator | Manage all users, editorial content, and application settings. |

## 3. Technology

| Area | Choice |
| --- | --- |
| Application | Django 5.1, Python 3.13, Gunicorn |
| Database | PostgreSQL 16 with pgvector image support |
| Styling/static files | Django static files plus WhiteNoise |
| Catalog source | TVmaze REST API |
| Containers | Docker Compose |
| HTTPS/public proxy | Existing server Caddy instance |
| Source control | GitHub, `jyb4/WatchVault` |
| Planned retrieval | PostgreSQL/pgvector, later Neo4j and RAG |

## 4. Content model

The primary catalog object is a `Show`. It stores a title, slug, synopsis, poster URL, premiere date, rating, network, genres, TVmaze source ID/link, import timestamp, and publishing status.

Imported entries begin as **drafts** by default. Editors review them in Django Admin before publishing. A deliberate `--publish` option exists for a known-good demo or seed import.

`WatchlistItem` links a signed-in member to a published show and prevents duplicates.

## 5. TVmaze integration

WatchVault imports a selected TVmaze search result rather than copying the entire TVmaze database.

```text
python manage.py import_tvmaze Severance
python manage.py import_tvmaze Severance --publish
```

The importer stores the source ID and URL, removes HTML from summaries, maps genres, handles connection/HTTP errors, and reports rate-limit failures. The site visibly credits TVmaze. Follow TVmaze's attribution and CC BY-SA requirements for all imported material.

## 6. Live architecture

```text
Browser
  ↓ HTTPS
Caddy on jybdeployment.com
  ↓ reverse proxy to 127.0.0.1:8080
WatchVault Gunicorn container
  ↓
PostgreSQL + pgvector container
```

Caddy owns ports 80 and 443 and must not be replaced by the WatchVault Compose stack. WatchVault binds only to loopback port `127.0.0.1:8080`.

The previous placeholder container is retained in a stopped state as `jyb-prod`; it is the immediate rollback option.

## 7. Environments and release process

### Local development

Use `compose.yaml` with `.env`. Docker Desktop must be running and the Windows account must be permitted to use its Docker engine.

### Server staging

Before a public release, start WatchVault on private port 8090:

```text
HOSTED_PORT=8090 docker compose --env-file .env.staging -f compose.production.yaml --project-name watchvault-staging up --build --detach
```

Verify its response locally on the server with the intended Host and `X-Forwarded-Proto: https` headers.

### Production promotion

1. Pull the approved `main` branch on the server.
2. Preserve a working fallback container.
3. Stop the active production container using port 8080.
4. Start WatchVault with `compose.production.yaml` and `HOSTED_PORT=8080`.
5. Verify `https://jybdeployment.com` returns `200 OK`, renders WatchVault, and serves the stylesheet.
6. Record the deployed commit and outcome in `PROJECT_LOG.md`.

## 8. Rollback

If a release is unhealthy, stop the WatchVault production project and restart the stopped placeholder or previous known-good container:

```text
sudo docker start jyb-prod
```

Do not remove a working fallback until the new release has been verified.

## 9. Security and privacy

- `.env.production` exists only on the server and has restricted permissions.
- Never commit Django keys, database passwords, SSH private keys, or API secrets.
- Production redirects HTTP to HTTPS, uses secure session/CSRF cookies, and enables HSTS.
- PostgreSQL is not publicly exposed.
- Data-changing watchlist actions require signed-in users, POST requests, and CSRF validation.
- API content must retain required attribution and should not include unlicensed third-party review text.

## 10. Current release

- **Address:** `https://jybdeployment.com`
- **Initial WatchVault production release:** 2026-11-17
- **Catalog:** 18 published TVmaze shows in the initial discovery collection
- **Public verification:** homepage and hashed stylesheet both returned HTTP 200 through Caddy

## 10.1 Discovery interface

The homepage uses a cinematic featured-show hero, horizontal editorial discovery rows, a persistent catalog search, and a future-facing AI Guide entry point. Search matches published titles, genres, networks, and show descriptions. The visual direction is intentionally poster-first and dark, with a WatchVault-specific electric-blue accent rather than a copy of any reference product.

## 10.2 Dashboard discovery layout

The QA dashboard evolves the discovery interface into an app-style experience while preserving WatchVault branding and behavior. It includes a desktop sidebar, mobile navigation dock, searchable top bar, editorial carousel, dynamic Trending Now and New to the Vault rails, and a visual My Watchlist collection. Carousel content is restricted to editor-featured shows; member-imported shows do not automatically appear on the home page.

## 11. Next milestones

1. Create the first Django administrator and editor account.
2. Add registration, watchlist removal from the list page, filters, and accessible interface refinements.
3. Add automated deployment using GitHub Actions only after server SSH deployment secrets are configured.
4. Add chunking and pgvector semantic search.
5. Add graph relationships and the source-linked RAG AI Guide.
