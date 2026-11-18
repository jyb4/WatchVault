from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from .models import Genre, Show, WatchlistItem


@override_settings(
    SECURE_SSL_REDIRECT=False,
    STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}},
)
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

    @patch("catalog.views.fetch_show")
    def test_signed_in_member_can_import_a_tvmaze_match_to_watchlist(self, fetch_show):
        user = get_user_model().objects.create_user(
            username="member", password="test-password"
        )
        fetch_show.return_value = {
            "id": 999,
            "name": "Imported on Demand",
            "summary": "A show saved from search.",
            "image": {},
            "premiered": "2026-01-01",
            "rating": {"average": 8.2},
            "genres": ["Drama"],
            "url": "https://www.tvmaze.com/shows/999/imported-on-demand",
        }
        self.client.force_login(user)

        response = self.client.post(reverse("tvmaze-import-watchlist", args=[999]))

        show = Show.objects.get(source_name="TVmaze", source_id="999")
        self.assertRedirects(response, show.get_absolute_url())
        self.assertEqual(show.status, Show.Status.PUBLISHED)
        self.assertFalse(show.featured_on_home)
        self.assertTrue(WatchlistItem.objects.filter(user=user, show=show).exists())

    def test_member_can_create_an_account(self):
        response = self.client.post(
            reverse("signup"),
            {"username": "new-member", "password1": "Secur3-passphrase!", "password2": "Secur3-passphrase!"},
        )

        self.assertRedirects(response, reverse("watchlist"))
        self.assertTrue(get_user_model().objects.filter(username="new-member").exists())
