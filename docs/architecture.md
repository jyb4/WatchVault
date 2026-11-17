# Architecture and delivery plan

## Technology choices

- **Django + PostgreSQL:** the CMS, account system, public application, and durable catalog data.
- **pgvector:** semantic-search support in the same database when RAG work begins.
- **Neo4j (optional Docker profile):** later graph relationships such as shared cast, genres, networks, and franchises. It is intentionally optional until relational catalog features are complete.
- **Docker Compose:** reproducible local development and a foundation for server deployment.

## TVmaze import boundary

TVmaze is the selected catalog source. The importer is a Django management command that begins with `GET /search/shows?q=<title>` and then stores the selected result's stable TVmaze ID. It must:

1. set an identifiable User-Agent;
2. validate the provider response;
3. upsert by provider name and provider ID;
4. retain source URL/attribution;
5. create or update **draft** content rather than auto-publishing;
6. record errors without exposing secrets;
7. back off and retry later after a HTTP 429 response; and
8. retain source URLs and display TVmaze attribution under its CC BY-SA terms.

TVmaze's public API is cached, rate-limited, and does not require an API key for this use. WatchVault will import a selected show rather than bulk-mirroring TVmaze, which keeps the first release editorially manageable.

## RAG design (later phase)

Only published, approved catalog content is eligible for retrieval. Long editorial text will be split by meaningful headings/paragraph groups and stored with show ID, title, URL, source, genre, publishing status, and content version. The AI Guide will retrieve relevant chunks, generate a concise answer, and link users to the supporting WatchVault show profiles.

## Delivery sequence

1. Foundation: repository, Docker, project brief, information architecture. **In progress.**
2. Catalog CMS: migrations, admin editorial workflow, API provider adapter, and import logging.
3. Member experience: responsive visual system, filtering, watchlist mutations, registration, and access controls.
4. Retrieval: embeddings, chunking, vector search, and source-linked RAG answers.
5. Graph: import/select relationships and related-show discovery.
6. Operations: tests, GitHub Actions, server environment variables, HTTPS reverse proxy, backups, analytics, performance review, and deployment documentation.
