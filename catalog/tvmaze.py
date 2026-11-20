"""Read-only TVmaze search support for WatchVault discovery."""

import json
import re
from datetime import date, timedelta
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache
from django.template.defaultfilters import slugify
from django.utils import timezone

from .models import ExternalSearchCache, Genre, Show


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

    normalized_query = query.casefold()
    persistent_cache = ExternalSearchCache.objects.filter(
        query=normalized_query,
        expires_at__gt=timezone.now(),
    ).first()
    if persistent_cache:
        cache.set(cache_key, persistent_cache.results, timeout=900)
        return persistent_cache.results

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
    for match in payload:
        show = match.get("show", {})
        image = show.get("image") or {}
        results.append(
            {
                "id": str(show.get("id", "")),
                "title": show.get("name", "Untitled show"),
                "summary": _plain_text(show.get("summary")),
                "poster_url": image.get("medium") or image.get("original", ""),
                "rating": (show.get("rating") or {}).get("average"),
                "weight": show.get("weight", 0),
                "genres": show.get("genres", []),
                "source_url": show.get("url", ""),
            }
        )

    cache.set(cache_key, results, timeout=900)
    ExternalSearchCache.objects.update_or_create(
        query=normalized_query,
        defaults={"results": results, "expires_at": timezone.now() + timedelta(minutes=15)},
    )
    return results


def fetch_show(source_id):
    """Fetch one TVmaze show by ID, returning None if TVmaze is unavailable."""
    cache_key = f"tvmaze-show:{source_id}"
    cached_show = cache.get(cache_key)
    if cached_show is not None:
        return cached_show

    request = Request(
        f"{settings.TVMAZE_BASE_URL}/shows/{source_id}",
        headers={"Accept": "application/json", "User-Agent": settings.TVMAZE_USER_AGENT},
    )
    try:
        with urlopen(request, timeout=8) as response:
            show = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None

    cache.set(cache_key, show, timeout=3600)
    return show


def fetch_show_episodes(source_id):
    """Return a cached, display-ready episode list for one TVmaze show."""
    cache_key = f"tvmaze-show-episodes:{source_id}"
    cached_episodes = cache.get(cache_key)
    if cached_episodes is not None:
        return cached_episodes

    request = Request(
        f"{settings.TVMAZE_BASE_URL}/shows/{source_id}/episodes",
        headers={"Accept": "application/json", "User-Agent": settings.TVMAZE_USER_AGENT},
    )
    try:
        with urlopen(request, timeout=8) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return []

    episodes = []
    for episode in payload:
        season = episode.get("season")
        number = episode.get("number")
        if not isinstance(season, int) or not isinstance(number, int) or season < 1 or number < 1:
            continue
        image = episode.get("image") or {}
        episodes.append({
            "season": season,
            "number": number,
            "title": episode.get("name") or f"Episode {number}",
            "summary": _plain_text(episode.get("summary")),
            "airdate": episode.get("airdate") or "",
            "runtime": episode.get("runtime"),
            "image_url": image.get("medium") or image.get("original") or "",
        })

    cache.set(cache_key, episodes, timeout=21600)
    return episodes


def fetch_web_schedule(on_date):
    """Return scheduled streaming episodes with their TVmaze show data embedded."""
    cache_key = f"tvmaze-web-schedule:{on_date.isoformat()}"
    cached_schedule = cache.get(cache_key)
    if cached_schedule is not None:
        return cached_schedule

    parameters = urlencode({"date": on_date.isoformat(), "embed": "show"})
    request = Request(
        f"{settings.TVMAZE_BASE_URL}/schedule/web?{parameters}",
        headers={"Accept": "application/json", "User-Agent": settings.TVMAZE_USER_AGENT},
    )
    try:
        with urlopen(request, timeout=12) as response:
            schedule = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return []

    cache.set(cache_key, schedule, timeout=3600)
    return schedule


def upsert_show(data, publish=False):
    """Store TVmaze data as a WatchVault show while preserving editorial placement."""
    premiered = data.get("premiered")
    try:
        premiered_on = date.fromisoformat(premiered) if premiered else None
    except ValueError:
        premiered_on = None

    image = data.get("image") or {}
    source_id = str(data["id"])
    defaults = {
        "title": data.get("name", "Untitled show"),
        "slug": f"{slugify(data.get('name', 'show'))[:210]}-{source_id}",
        "synopsis": _plain_text(data.get("summary")),
        "poster_url": image.get("medium") or image.get("original", ""),
        "premiered_on": premiered_on,
        "external_rating": (data.get("rating") or {}).get("average"),
        "network": (data.get("network") or data.get("webChannel") or {}).get("name", ""),
        "source_url": data.get("url", ""),
        "import_updated_at": timezone.now(),
    }
    show, created = Show.objects.get_or_create(
        source_name="TVmaze",
        source_id=source_id,
        defaults={**defaults, "status": Show.Status.PUBLISHED if publish else Show.Status.DRAFT},
    )
    if not created:
        for field, value in defaults.items():
            setattr(show, field, value)
        if publish:
            show.status = Show.Status.PUBLISHED
        show.save()

    show.genres.set(
        [Genre.objects.get_or_create(name=name, defaults={"slug": slugify(name)})[0] for name in data.get("genres", [])]
    )
    return show, created
