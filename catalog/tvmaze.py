"""Read-only TVmaze search support for WatchVault discovery."""

import json
import re
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache


def _plain_text(value):
    """Turn TVmaze's short HTML summaries into safe card text."""
    without_tags = re.sub(r"<[^>]+>", "", unescape(value or ""))
    return re.sub(r"\s+", " ", without_tags).strip()


def search_shows(query):
    """Return a small, cached set of public TVmaze search matches."""
    cache_key = f"tvmaze-search:{query.casefold()}"
    cached_results = cache.get(cache_key)
    if cached_results is not None:
        return cached_results

    url = f"{settings.TVMAZE_BASE_URL}/search/shows?{urlencode({'q': query})}"
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": settings.TVMAZE_USER_AGENT},
    )
    try:
        with urlopen(request, timeout=8) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return []

    results = []
    for match in payload[:12]:
        show = match.get("show", {})
        image = show.get("image") or {}
        results.append(
            {
                "id": str(show.get("id", "")),
                "title": show.get("name", "Untitled show"),
                "summary": _plain_text(show.get("summary")),
                "poster_url": image.get("medium") or image.get("original", ""),
                "rating": (show.get("rating") or {}).get("average"),
                "genres": show.get("genres", []),
                "source_url": show.get("url", ""),
            }
        )

    cache.set(cache_key, results, timeout=900)
    return results
