from unittest.mock import patch
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from .models import ExternalSearchCache, Genre, SearchIndexEntry, Show, WatchlistItem
from .tvmaze import search_shows


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

    @patch("catalog.views.search_tvmaze_shows")
    def test_local_search_returns_matching_catalog_shows_without_calling_tvmaze(self, tvmaze_search):
        Show.objects.create(title="The Flash", slug="the-flash", status=Show.Status.PUBLISHED)

        response = self.client.get(reverse("local-search"), {"q": "flash"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["title"], "The Flash")
        tvmaze_search.assert_not_called()

    def test_local_search_uses_popular_title_index_for_prefixes(self):
        SearchIndexEntry.objects.create(
            source_name="TVmaze", source_id="13", title="The Flash",
            source_url="https://example.com/the-flash", external_rating=7.6,
        )

        response = self.client.get(reverse("local-search"), {"q": "fla"})

        self.assertEqual(response.json()["results"][0]["title"], "The Flash")

    def test_local_search_does_not_match_only_one_word_of_a_multiword_query(self):
        SearchIndexEntry.objects.create(source_name="TVmaze", source_id="52", title="How to Get Away with Murder")

        response = self.client.get(reverse("local-search"), {"q": "how its made"})

        self.assertEqual(response.json()["results"], [])

    @patch("catalog.views.search_tvmaze_shows")
    def test_external_search_excludes_titles_already_imported(self, tvmaze_search):
        Show.objects.create(
            title="The Flash", slug="the-flash", status=Show.Status.PUBLISHED,
            source_name="TVmaze", source_id="1",
        )
        tvmaze_search.return_value = [
            {"id": "1", "title": "The Flash", "poster_url": "", "source_url": "https://example.com/flash"},
            {"id": "2", "title": "Flashpoint", "poster_url": "", "source_url": "https://example.com/flashpoint"},
        ]

        response = self.client.get(reverse("external-search"), {"q": "flash"})

        self.assertEqual(response.json()["results"], [{
            "title": "Flashpoint", "meta": "TVmaze match", "poster": "",
            "url": "https://example.com/flashpoint", "source": "TVmaze",
        }])

    @patch("catalog.views.search_tvmaze_shows")
    def test_external_search_relaxes_an_unfinished_final_word(self, tvmaze_search):
        tvmaze_search.side_effect = [[], [{
            "id": "52", "title": "How to Get Away with Murder", "poster_url": "",
            "source_url": "https://example.com/how-to-get-away", "rating": 8.1,
        }]]

        response = self.client.get(reverse("external-search"), {"q": "how to get away with qwerty"})

        self.assertEqual(response.json()["results"][0]["title"], "How to Get Away with Murder")
        self.assertEqual(tvmaze_search.call_args_list[1].args[0], "how to get away with")

    @patch("catalog.views.search_tvmaze_shows")
    def test_external_search_excludes_titles_already_in_popular_index(self, tvmaze_search):
        SearchIndexEntry.objects.create(source_name="TVmaze", source_id="13", title="The Flash")
        tvmaze_search.return_value = [{
            "id": "13", "title": "The Flash", "poster_url": "",
            "source_url": "https://example.com/the-flash", "rating": 7.6,
        }]

        response = self.client.get(reverse("external-search"), {"q": "flash"})

        self.assertEqual(response.json()["results"], [])

    @patch("catalog.tvmaze.urlopen")
    def test_tvmaze_search_reuses_shared_database_cache(self, urlopen):
        ExternalSearchCache.objects.create(
            query="shared-cache-check",
            results=[{"id": "1", "title": "The Flash"}],
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        self.assertEqual(search_shows("shared-cache-check"), [{"id": "1", "title": "The Flash"}])
        urlopen.assert_not_called()
