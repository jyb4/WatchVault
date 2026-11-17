"""Import one selected TVmaze show as an editorial draft."""
import re
from datetime import date
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.template.defaultfilters import slugify
from django.utils import timezone

from catalog.models import Genre, Show


def plain_text(value):
    """Turn TVmaze's HTML summary into readable plain text."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", unescape(value or ""))).strip()


class Command(BaseCommand):
    help = "Search TVmaze and import the best match as a WatchVault draft."

    def add_arguments(self, parser):
        parser.add_argument("query", help="TV show title to search for")
        parser.add_argument("--tvmaze-id", type=int, help="Import a known TVmaze show ID instead of searching")

    def handle(self, *args, **options):
        show_data = self.fetch_show(options["query"], options.get("tvmaze_id"))
        show, created = self.save_show(show_data)
        action = "Imported" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} draft: {show.title} (TVmaze #{show.source_id})"))

    def fetch_json(self, path, parameters=None):
        query = f"?{urlencode(parameters, doseq=True)}" if parameters else ""
        request = Request(
            f"{settings.TVMAZE_BASE_URL}{path}{query}",
            headers={"Accept": "application/json", "User-Agent": settings.TVMAZE_USER_AGENT},
        )
        try:
            with urlopen(request, timeout=15) as response:
                return __import__("json").load(response)
        except HTTPError as error:
            if error.code == 429:
                raise CommandError("TVmaze rate limit reached. Wait a few seconds and try again.") from error
            raise CommandError(f"TVmaze returned HTTP {error.code}.") from error
        except URLError as error:
            raise CommandError(f"Could not connect to TVmaze: {error.reason}") from error

    def fetch_show(self, query, tvmaze_id):
        if tvmaze_id:
            return self.fetch_json(f"/shows/{tvmaze_id}")
        matches = self.fetch_json("/search/shows", {"q": query})
        if not matches:
            raise CommandError(f"No TVmaze show matched '{query}'.")
        return matches[0]["show"]

    def save_show(self, data):
        premiered = data.get("premiered")
        try:
            premiered_on = date.fromisoformat(premiered) if premiered else None
        except ValueError:
            premiered_on = None

        image = data.get("image") or {}
        network = (data.get("network") or data.get("webChannel") or {}).get("name", "")
        source_id = str(data["id"])
        defaults = {
            "title": data["name"],
            "slug": self.unique_slug(data["name"], source_id),
            "synopsis": plain_text(data.get("summary")),
            "poster_url": image.get("medium") or image.get("original", ""),
            "premiered_on": premiered_on,
            "external_rating": (data.get("rating") or {}).get("average"),
            "network": network,
            "source_url": (data.get("url") or ""),
            "import_updated_at": timezone.now(),
            "status": Show.Status.DRAFT,
        }
        show, created = Show.objects.update_or_create(source_name="TVmaze", source_id=source_id, defaults=defaults)
        show.genres.set([Genre.objects.get_or_create(name=name, defaults={"slug": slugify(name)})[0] for name in data.get("genres", [])])
        return show, created

    @staticmethod
    def unique_slug(title, source_id):
        return f"{slugify(title)[:210]}-{source_id}"
