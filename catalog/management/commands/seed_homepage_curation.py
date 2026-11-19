"""Seed a reviewed starting collection without making scheduled imports homepage content."""

from django.core.management.base import BaseCommand

from catalog.models import Show


CURATED_TITLES = (
    "Fargo", "Fringe", "Arcane: League of Legends", "Dexter", "Narcos",
    "Dark", "Hannibal", "Lost", "Ozark", "Silo", "Andor", "Wednesday",
    "Foundation", "Severance", "Kongen Befaler",
)


class Command(BaseCommand):
    help = "Seed a quality-reviewed starter homepage collection from known catalog titles."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Save the planned curation changes")
        parser.add_argument("--replace", action="store_true", help="Clear existing homepage curation flags first")

    def handle(self, *args, **options):
        selected = list(Show.objects.filter(
            status=Show.Status.PUBLISHED,
            title__in=CURATED_TITLES,
            poster_url__gt="",
            synopsis__gt="",
        ))
        selected_by_title = {show.title: show for show in selected}
        ordered = [selected_by_title[title] for title in CURATED_TITLES if title in selected_by_title]
        self.stdout.write(f"Prepared {len(ordered)} editorially reviewed homepage titles.")
        if not options["apply"]:
            self.stdout.write("Dry run only. Re-run with --apply to save these placements.")
            return

        if options["replace"]:
            Show.objects.update(featured_on_home=False, homepage_trending=False, homepage_fresh=False, editorial_priority=0)
        for position, show in enumerate(ordered, start=1):
            show.featured_on_home = position <= 5
            show.homepage_trending = position <= 10
            # A few editor pins lead Fresh; the remaining slots fill from the daily quality import.
            show.homepage_fresh = 6 <= position <= 8
            show.editorial_priority = len(ordered) - position + 1
            show.save(update_fields=("featured_on_home", "homepage_trending", "homepage_fresh", "editorial_priority"))
        self.stdout.write(self.style.SUCCESS("Homepage curation saved."))
