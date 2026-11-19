"""Bring recent and upcoming TVmaze schedule shows into the public discovery catalog."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from catalog.tvmaze import fetch_web_schedule, upsert_show


class Command(BaseCommand):
    help = "Import unique shows from TVmaze's web schedule for homepage discovery."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=7, help="Number of upcoming schedule days to inspect")
        parser.add_argument("--limit", type=int, default=36, help="Maximum number of unique shows to import")

    def handle(self, *args, **options):
        days = max(1, options["days"])
        limit = max(1, options["limit"])
        today = timezone.localdate()
        seen_ids = set()
        imported = 0
        created = 0

        for offset in range(days):
            for episode in fetch_web_schedule(today + timedelta(days=offset)):
                show_data = (episode.get("_embedded") or {}).get("show") or episode.get("show")
                if not isinstance(show_data, dict) or not show_data.get("id"):
                    continue
                source_id = str(show_data["id"])
                if source_id in seen_ids:
                    continue
                seen_ids.add(source_id)
                _show, was_created = upsert_show(show_data, publish=True)
                imported += 1
                created += int(was_created)
                if imported >= limit:
                    break
            if imported >= limit:
                break

        self.stdout.write(self.style.SUCCESS(
            f"Synchronized {imported} TV shows from the upcoming schedule ({created} new)."
        ))
