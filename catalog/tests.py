from unittest.mock import patch

from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from .models import Genre, Show


@override_settings(SECURE_SSL_REDIRECT=False)
class CatalogVisibilityTests(TestCase):
    def test_drafts_are_not_visible_in_public_catalog(self):
        Show.objects.create(title="Unpublished Show", slug="unpublished-show")
        response = self.client.get(reverse("show-list"))
        self.assertNotContains(response, "Unpublished Show")

    def test_published_show_is_visible_in_public_catalog(self):
        Show.objects.create(title="Published Show", slug="published-show", status=Show.Status.PUBLISHED)
        response = self.client.get(reverse("show-list"))
        self.assertContains(response, "Published Show")

    @patch("catalog.views.search_tvmaze_shows", return_value=[])
    def test_catalog_search_matches_a_genre(self, _tvmaze_search):
        genre = Genre.objects.create(name="Science-Fiction", slug="science-fiction")
        show = Show.objects.create(title="The Signal", slug="the-signal", status=Show.Status.PUBLISHED)
        show.genres.add(genre)
        self.assertContains(self.client.get(reverse("show-list"), {"q": "science"}), "The Signal")

    @patch("catalog.views.search_tvmaze_shows")
    def test_catalog_search_includes_tvmaze_matches_not_in_local_catalog(self, tvmaze_search):
        tvmaze_search.return_value = [{"id": "999", "title": "Unimported Match", "summary": "A show found by TVmaze.", "poster_url": "", "rating": 8.5, "genres": ["Drama"], "source_url": "https://www.tvmaze.com/shows/999/unimported-match"}]
        response = self.client.get(reverse("show-list"), {"q": "unimported"})
        self.assertContains(response, "Unimported Match")
        self.assertContains(response, "More matches from TVmaze")
