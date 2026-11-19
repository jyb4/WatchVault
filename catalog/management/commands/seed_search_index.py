from django.core.management.base import BaseCommand

from catalog.models import SearchIndexEntry
from catalog.tvmaze import search_shows


POPULAR_TITLES = [
    "The Flash", "How to Get Away with Murder", "Breaking Bad", "Game of Thrones",
    "Stranger Things", "The Office", "Friends", "Better Call Saul", "The Boys",
    "The Last of Us", "House of the Dragon", "The Bear", "Dexter", "Narcos",
]


class Command(BaseCommand):
    help = "Seed WatchVault's lightweight popular-TV autocomplete index from TVmaze."

    def handle(self, *args, **options):
        created_count = 0
        for title in POPULAR_TITLES:
            match = next((show for show in search_shows(title) if show["title"].casefold() == title.casefold()), None)
            if not match:
                self.stderr.write(f"No exact TVmaze match for {title}")
                continue
            _entry, created = SearchIndexEntry.objects.update_or_create(
                source_name="TVmaze",
                source_id=match["id"],
                defaults={
                    "title": match["title"],
                    "poster_url": match["poster_url"],
                    "source_url": match["source_url"],
                    "external_rating": match.get("rating"),
                    "popularity_boost": 100,
                },
            )
            created_count += int(created)
        self.stdout.write(self.style.SUCCESS(f"Popular search index ready ({created_count} new entries)."))
