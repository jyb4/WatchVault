# Information architecture

## Public navigation

```text
WatchVault
├── Home
├── Discover
│   ├── Search results
│   └── Show detail
├── My Watchlist (members)
├── AI Guide (planned)
└── Sign in
```

## CMS navigation

```text
Admin dashboard
├── Shows
│   ├── Drafts awaiting editorial review
│   └── Published catalog
├── Genres
├── Imports and errors (planned)
├── Users and roles
└── AI content index (planned)
```

## Core user journeys

### Discover and save

Visitor searches or browses → opens a show profile → signs in when prompted → adds that show to My Watchlist.

### Import and publish

Editor starts an API import → validation and duplicate checks run → show enters as a draft → editor corrects/enriches the profile → editor publishes it.
