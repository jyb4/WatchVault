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

    def test_member_can_track_status_and_progress_for_own_show(self):
        user = get_user_model().objects.create_user(username="viewer", password="test-password")
        show = Show.objects.create(title="Tracked Show", slug="tracked-show", status=Show.Status.PUBLISHED)
        item = WatchlistItem.objects.create(user=user, show=show)
        previous_update = item.last_updated_at
        self.client.force_login(user)

        response = self.client.post(reverse("watchlist-update", args=[show.slug]), {
            "status": WatchlistItem.Status.WATCHING,
            "current_season": "2",
            "current_episode": "4",
        })

        self.assertRedirects(response, show.get_absolute_url())
        item.refresh_from_db()
        self.assertEqual(item.status, WatchlistItem.Status.WATCHING)
        self.assertEqual(item.current_season, 2)
        self.assertEqual(item.current_episode, 4)
        self.assertGreaterEqual(item.last_updated_at, previous_update)

    def test_member_cannot_update_someone_elses_watchlist_item(self):
        owner = get_user_model().objects.create_user(username="owner", password="test-password")
        other_user = get_user_model().objects.create_user(username="other", password="test-password")
        show = Show.objects.create(title="Private Tracking", slug="private-tracking", status=Show.Status.PUBLISHED)
        item = WatchlistItem.objects.create(user=owner, show=show)
        self.client.force_login(other_user)

        response = self.client.post(reverse("watchlist-update", args=[show.slug]), {"status": "completed"})

        self.assertEqual(response.status_code, 404)
        item.refresh_from_db()
        self.assertEqual(item.status, WatchlistItem.Status.PLAN_TO_WATCH)

    def test_tracking_rejects_an_episode_without_a_season(self):
        user = get_user_model().objects.create_user(username="validator", password="test-password")
        show = Show.objects.create(title="Validated Show", slug="validated-show", status=Show.Status.PUBLISHED)
        WatchlistItem.objects.create(user=user, show=show)
        self.client.force_login(user)

        response = self.client.post(reverse("watchlist-update", args=[show.slug]), {
            "status": "watching", "current_episode": "3",
        })

        self.assertEqual(response.status_code, 400)

    @patch("catalog.views.fetch_show_episodes")
    def test_show_detail_displays_public_episode_guide(self, fetch_show_episodes):
        show = Show.objects.create(
            title="Episode Guide", slug="episode-guide", status=Show.Status.PUBLISHED,
            source_name="TVmaze", source_id="401",
        )
        fetch_show_episodes.return_value = [{
            "season": 1, "number": 1, "title": "Pilot", "summary": "The story begins.",
            "airdate": "2026-01-01", "runtime": 45, "image_url": "https://example.com/pilot.jpg",
        }]

        response = self.client.get(show.get_absolute_url())

        self.assertContains(response, "Explore every season")
        self.assertContains(response, "Pilot")
        self.assertContains(response, "Sign in to track")

    @patch("catalog.views.fetch_show_episodes")
    def test_member_can_set_progress_from_a_verified_episode(self, fetch_show_episodes):
        user = get_user_model().objects.create_user(username="episode-viewer", password="test-password")
        show = Show.objects.create(
            title="Episode Progress", slug="episode-progress", status=Show.Status.PUBLISHED,
            source_name="TVmaze", source_id="402",
        )
        fetch_show_episodes.return_value = [{
            "season": 2, "number": 6, "title": "Chapter Six", "summary": "", "airdate": "", "runtime": None, "image_url": "https://example.com/chapter-six.jpg",
        }]
        self.client.force_login(user)

        response = self.client.post(reverse("watchlist-episode-progress", args=[show.slug]), {"season": "2", "episode": "6"})

        self.assertRedirects(response, show.get_absolute_url())
        item = WatchlistItem.objects.get(user=user, show=show)
        self.assertEqual(item.status, WatchlistItem.Status.WATCHING)
        self.assertEqual((item.current_season, item.current_episode), (2, 6))
        self.assertEqual(item.current_episode_image_url, "https://example.com/chapter-six.jpg")

    @patch("catalog.views.fetch_show_episodes", return_value=[])
    def test_episode_progress_rejects_an_episode_not_returned_by_tvmaze(self, _episodes):
        user = get_user_model().objects.create_user(username="episode-validator", password="test-password")
        show = Show.objects.create(
            title="No Episode", slug="no-episode", status=Show.Status.PUBLISHED,
            source_name="TVmaze", source_id="403",
        )
        self.client.force_login(user)

        response = self.client.post(reverse("watchlist-episode-progress", args=[show.slug]), {"season": "1", "episode": "1"})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(WatchlistItem.objects.filter(user=user, show=show).exists())

    def test_home_continue_watching_only_includes_watching_items_in_update_order(self):
        user = get_user_model().objects.create_user(username="home-viewer", password="test-password")
        older = Show.objects.create(title="Older Progress", slug="older-progress", status=Show.Status.PUBLISHED, poster_url="https://example.com/older.jpg", synopsis="A complete show.")
        newer = Show.objects.create(title="Newer Progress", slug="newer-progress", status=Show.Status.PUBLISHED, poster_url="https://example.com/newer.jpg", synopsis="A complete show.")
        planned = Show.objects.create(title="Planned Only", slug="planned-only", status=Show.Status.PUBLISHED, poster_url="https://example.com/planned.jpg", synopsis="A complete show.")
        WatchlistItem.objects.create(user=user, show=older, status=WatchlistItem.Status.WATCHING, current_season=1, current_episode=2, last_updated_at=timezone.now() - timedelta(days=1))
        WatchlistItem.objects.create(user=user, show=newer, status=WatchlistItem.Status.WATCHING, current_season=3, current_episode=5)
        WatchlistItem.objects.create(user=user, show=planned, status=WatchlistItem.Status.PLAN_TO_WATCH)
        self.client.force_login(user)

        response = self.client.get(reverse("home"))

        self.assertContains(response, "Continue Watching")
        self.assertContains(response, "Season 3 · Episode 5")
        self.assertEqual(
            [item.show.title for item in response.context["continue_watching_items"]],
            ["Newer Progress", "Older Progress"],
        )
        self.assertLess(response.content.find(b"Newer Progress"), response.content.find(b"Older Progress"))

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

    def test_local_search_normalizes_punctuation_in_indexed_titles(self):
        SearchIndexEntry.objects.create(source_name="TVmaze", source_id="999", title="How It's Made")

        response = self.client.get(reverse("local-search"), {"q": "how its made"})

        self.assertEqual(response.json()["results"][0]["title"], "How It's Made")

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
    def test_external_search_prioritizes_popularity_after_prefix_match(self, tvmaze_search):
        tvmaze_search.return_value = [
            {"id": "1", "title": "Flash Gordon", "poster_url": "", "source_url": "https://example.com/gordon", "rating": 7.0, "weight": 10},
            {"id": "2", "title": "The Flash", "poster_url": "", "source_url": "https://example.com/flash", "rating": 7.6, "weight": 100},
        ]

        response = self.client.get(reverse("external-search"), {"q": "fla"})

        self.assertEqual(response.json()["results"][0]["title"], "The Flash")

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
