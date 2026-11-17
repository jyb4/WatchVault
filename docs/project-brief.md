# WatchVault project brief

## Product vision

WatchVault is a self-hosted TV-show discovery platform. It combines a curated editorial catalog with personal watchlists and, later, a transparent AI Guide that recommends only from published WatchVault content.

## Audience and roles

| Role | Primary goal | Permissions |
| --- | --- | --- |
| Visitor | Discover a new show | Browse published catalog and search |
| Member | Keep track of shows to watch | Visitor access plus personal watchlist |
| Editor | Curate accurate, useful content | Import, edit, draft, and publish shows |
| Administrator | Operate the service safely | Manage users, roles, configuration, and all content |

## Content strategy

The site will manage TV-show profiles: title, synopsis, image, premiere date, rating, genres, network, source attribution, and editorial publishing status. API data is imported as a draft, reviewed by an editor, then published. The site will not copy unlicensed full articles or reviews. Images and provider material must follow the selected API's terms and retain required attribution.

## Success criteria for the first release

1. Editors can import and publish TV-show profiles.
2. Visitors can browse and search published shows.
3. Members can securely sign in and manage a watchlist.
4. The app runs locally and on the project server through Docker.
5. The catalog data model can later support vector search, graph relationships, and RAG.
