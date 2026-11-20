from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
import re
from difflib import SequenceMatcher

from django.db.models import F, Q
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView
from .models import SearchIndexEntry, Show, WatchlistItem
from .tvmaze import fetch_show, fetch_show_episodes, search_shows as search_tvmaze_shows, upsert_show


def signup(request):
    next_url = request.POST.get("next") or request.GET.get("next", "")
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            if url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
                return redirect(next_url)
            return redirect("watchlist")
    else:
        form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form, "next": next_url})


def _search_result(show):
    return {
        "title": show.title,
        "meta": f"TV · {show.premiered_on.year}" if show.premiered_on else "TV series",
        "poster": show.poster_url,
        "url": show.get_absolute_url(),
        "source": "WatchVault",
    }


def _normalized_words(value):
    value = re.sub(r"['’]", "", (value or "").casefold())
    return re.findall(r"[a-z0-9]+", value)


def _ordered_word_match_count(title_words, query_words):
    position = 0
    matched_words = 0
    for query_word in query_words:
        while position < len(title_words) and not title_words[position].startswith(query_word):
            position += 1
        if position == len(title_words):
            break
        matched_words += 1
        position += 1
    return matched_words


def _match_score(title, query, rating=0, popularity_boost=0, weight=0):
    """Rank title relevance first, then TVmaze popularity and rating."""
    title_words = _normalized_words(title)
    query_words = _normalized_words(query)
    if not title_words or not query_words:
        return 0

    title_text = " ".join(title_words)
    query_text = " ".join(query_words)
    if title_text == query_text:
        relevance = 1_000_000
    else:
        matched_words = _ordered_word_match_count(title_words, query_words)
        if matched_words == len(query_words):
            relevance = 900_000
        else:
            similarity = SequenceMatcher(None, query_text, title_text).ratio()
            if similarity < 0.72:
                return 0
            relevance = 100_000 + int(similarity * 10_000)

    return relevance + int(float(weight or 0) * 100) + int(float(rating or 0) * 10) + popularity_boost


def _index_result(entry):
    return {
        "title": entry.title,
        "meta": "TVmaze match",
        "poster": entry.poster_url,
        "url": entry.source_url,
        "source": "TVmaze",
    }


def _index_match_score(entry, query):
    return max(
        _match_score(candidate, query, entry.external_rating, entry.popularity_boost)
        for candidate in [entry.title, *(entry.aliases or [])]
    )


def local_search(request):
    """Return catalog matches immediately, without waiting for an external service."""
    query = request.GET.get("q", "").strip()
    local_shows = Show.objects.filter(status=Show.Status.PUBLISHED)
    if query:
        local_shows = local_shows.filter(Q(title__icontains=query)).distinct()
    local_shows = local_shows.order_by("-external_rating", "title")[:8]
    ranked_results = [
        (_search_result(show), _match_score(show.title, query, show.external_rating))
        for show in local_shows
    ]
    imported_source_ids = {
        (show.source_name, show.source_id)
        for show in local_shows
        if show.source_name and show.source_id
    }
    index_entries = SearchIndexEntry.objects.all()
    if query:
        index_entries = [
            entry for entry in index_entries
            if _index_match_score(entry, query)
        ]
    else:
        index_entries = index_entries.order_by("-popularity_boost", "-external_rating", "title")[:8]
    for entry in index_entries:
        if (entry.source_name, entry.source_id) not in imported_source_ids:
            ranked_results.append((
                _index_result(entry),
                _index_match_score(entry, query),
            ))
    ranked_results.sort(key=lambda candidate: candidate[1], reverse=True)
    return JsonResponse({"query": query, "results": [item for item, _score in ranked_results[:8]]})


def external_search(request):
    """Fetch supplemental TVmaze matches after the local catalog is already visible."""
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"query": query, "results": []})

    tvmaze_matches = search_tvmaze_shows(query)[:12]
    existing_source_ids = set(
        Show.objects.filter(
            status=Show.Status.PUBLISHED,
            source_name="TVmaze",
            source_id__in=[show["id"] for show in tvmaze_matches],
        ).values_list("source_id", flat=True)
    )
    existing_source_ids.update(
        SearchIndexEntry.objects.filter(
            source_name="TVmaze",
            source_id__in=[show["id"] for show in tvmaze_matches],
        ).values_list("source_id", flat=True)
    )
    ranked_matches = [
        (show, _match_score(show["title"], query, show.get("rating"), weight=show.get("weight", 0)))
        for show in tvmaze_matches
        if show["id"] not in existing_source_ids
    ]
    ranked_matches = [(show, score) for show, score in ranked_matches if score]
    ranked_matches.sort(key=lambda candidate: candidate[1], reverse=True)
    results = [{
        "title": show["title"], "meta": "TVmaze match", "poster": show["poster_url"],
        "url": show["source_url"], "source": "TVmaze",
    } for show, _score in ranked_matches]
    return JsonResponse({"query": query, "results": results[:8]})


class HomeView(ListView):
    template_name = "catalog/home.html"
    context_object_name = "featured_shows"

    def get_queryset(self):
        return self._homepage_ready().filter(
            status=Show.Status.PUBLISHED,
            featured_on_home=True,
        ).order_by("-editorial_priority", F("external_rating").desc(nulls_last=True), "title")[:17]

    @staticmethod
    def _homepage_ready():
        """Only use complete, poster-ready records in visual homepage placements."""
        return Show.objects.filter(
            status=Show.Status.PUBLISHED,
            poster_url__gt="",
            synopsis__gt="",
        ).prefetch_related("genres")

    @staticmethod
    def _decorate_up_next_item(item):
        """Attach lightweight episode-guide details used by the home tracker card."""
        item.current_episode_title = "Choose an episode"
        item.season_episode_total = 0
        item.progress_percent = 0
        item.is_season_finale = False
        show = item.show
        if not (show.source_name == "TVmaze" and show.source_id and item.current_season and item.current_episode):
            return item

        episodes = fetch_show_episodes(show.source_id)
        season_episodes = [entry for entry in episodes if entry["season"] == item.current_season]
        selected_index = next((
            index for index, entry in enumerate(season_episodes)
            if entry["number"] == item.current_episode
        ), None)
        if selected_index is None:
            return item
        selected = season_episodes[selected_index]
        item.current_episode_title = selected["title"]
        item.season_episode_total = len(season_episodes)
        item.progress_percent = round((selected_index / len(season_episodes)) * 100) if season_episodes else 0
        item.is_season_finale = selected_index == len(season_episodes) - 1
        return item

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shows = list(context["featured_shows"])
        context["hero_slides"] = shows[:5]
        homepage_ready = self._homepage_ready()
        trending = homepage_ready.filter(homepage_trending=True).order_by(
            "-editorial_priority", F("external_rating").desc(nulls_last=True), "title"
        )
        context["trending"] = trending[:10] if trending.exists() else shows[:10]
        top_rated = list(homepage_ready.order_by(F("external_rating").desc(nulls_last=True), "title")[:15])
        context["top_rated"] = top_rated
        pinned_fresh = list(homepage_ready.filter(homepage_fresh=True).order_by(
            "-editorial_priority", "-import_updated_at", "title"
        )[:14])
        automatic_fresh = homepage_ready.exclude(pk__in=[show.pk for show in pinned_fresh]).filter(
            external_rating__isnull=False,
        ).order_by("-import_updated_at", "-created_at")
        fresh = (pinned_fresh + list(automatic_fresh[:max(0, 14 - len(pinned_fresh))]))[:14]
        context["recently_added"] = fresh[:7]
        context["fresh_this_week"] = fresh[7:14]
        displayed_ids = {show.pk for show in top_rated + fresh}
        context["more_to_explore"] = homepage_ready.exclude(pk__in=displayed_ids).order_by(
            "-editorial_priority", F("external_rating").desc(nulls_last=True), "title"
        )[:20]
        context["continue_watching_items"] = []
        context["watchlist_show_ids"] = set()
        if self.request.user.is_authenticated:
            context["watchlist_show_ids"] = set(WatchlistItem.objects.filter(
                user=self.request.user
            ).values_list("show_id", flat=True))
            items = WatchlistItem.objects.filter(
                user=self.request.user,
                status=WatchlistItem.Status.WATCHING,
            ).select_related("show").prefetch_related("show__genres").order_by("-last_updated_at")[:8]
            context["continue_watching_items"] = [self._decorate_up_next_item(item) for item in items]
        return context


class ShowListView(ListView):
    template_name = "catalog/show_list.html"
    context_object_name = "shows"

    def get_queryset(self):
        shows = Show.objects.filter(status=Show.Status.PUBLISHED).prefetch_related("genres")
        query = self.request.GET.get("q", "").strip()
        if query:
            shows = shows.filter(Q(title__icontains=query) | Q(synopsis__icontains=query) | Q(network__icontains=query) | Q(genres__name__icontains=query)).distinct()
        return shows.order_by("-external_rating", "title")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()
        context["query"] = query
        context["external_results"] = []
        if query:
            local_source_ids = set(
                Show.objects.filter(
                    status=Show.Status.PUBLISHED,
                    source_name="TVmaze",
                ).values_list("source_id", flat=True)
            )
            context["external_results"] = [
                result
                for result in search_tvmaze_shows(query)
                if result["id"] not in local_source_ids
            ]
        return context


class ShowDetailView(DetailView):
    template_name = "catalog/show_detail.html"
    queryset = Show.objects.filter(status=Show.Status.PUBLISHED).prefetch_related("genres")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["watchlist_item"] = None
        if self.request.user.is_authenticated:
            context["watchlist_item"] = WatchlistItem.objects.filter(
                user=self.request.user, show=self.object
            ).first()
        context["watchlist_statuses"] = WatchlistItem.Status.choices
        episodes = []
        if self.object.source_name == "TVmaze" and self.object.source_id:
            episodes = fetch_show_episodes(self.object.source_id)
        seasons = {}
        for episode in episodes:
            seasons.setdefault(episode["season"], []).append(episode)
        context["episode_seasons"] = sorted(seasons.items())
        return context


class WatchlistView(LoginRequiredMixin, ListView):
    template_name = "catalog/watchlist.html"
    context_object_name = "items"

    def get_queryset(self):
        return WatchlistItem.objects.filter(user=self.request.user).select_related("show").prefetch_related("show__genres")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["items"] = [HomeView._decorate_up_next_item(item) for item in context["items"]]
        context["watchlist_statuses"] = WatchlistItem.Status.choices
        return context


@login_required
@require_POST
def add_to_watchlist(request, slug):
    show = get_object_or_404(Show, slug=slug, status=Show.Status.PUBLISHED)
    item, _created = WatchlistItem.objects.get_or_create(user=request.user, show=show)
    return _watchlist_response(request, show, "added", item)


@login_required
@require_POST
def remove_from_watchlist(request, slug):
    show = get_object_or_404(Show, slug=slug, status=Show.Status.PUBLISHED)
    WatchlistItem.objects.filter(user=request.user, show=show).delete()
    return _watchlist_response(request, show, "removed")


def _progress_value(request, field_name):
    value = request.POST.get(field_name, "").strip()
    if not value:
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name.replace('_', ' ').capitalize()} must be a whole number.")
    if number < 1:
        raise ValueError(f"{field_name.replace('_', ' ').capitalize()} must be at least 1.")
    return number


def _watchlist_redirect(request, show):
    next_url = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
        return redirect(next_url)
    return redirect(show)


def _watchlist_response(request, show, action, item=None, episodes=None):
    """Keep form redirects as a fallback while supporting in-place UI updates."""
    if "application/json" not in request.headers.get("Accept", ""):
        return _watchlist_redirect(request, show)

    payload = {"action": action, "show_slug": show.slug}
    if item is not None:
        payload.update({
            "status": item.status,
            "status_display": item.get_status_display(),
            "season": item.current_season,
            "episode": item.current_episode,
        })
        if episodes and item.current_season and item.current_episode:
            season_episodes = [entry for entry in episodes if entry["season"] == item.current_season]
            current_index = next((
                index for index, entry in enumerate(season_episodes)
                if entry["number"] == item.current_episode
            ), None)
            if current_index is not None:
                current_episode = season_episodes[current_index]
                payload.update({
                    "episode_title": current_episode["title"],
                    "season_episode_total": len(season_episodes),
                    "progress_percent": round((current_index / len(season_episodes)) * 100) if season_episodes else 0,
                    "is_season_finale": current_index == len(season_episodes) - 1,
                })
    return JsonResponse(payload)


@login_required
@require_POST
def update_watchlist_item(request, slug):
    """Save one member's tracking status and optional viewing progress."""
    show = get_object_or_404(Show, slug=slug, status=Show.Status.PUBLISHED)
    item = get_object_or_404(WatchlistItem, user=request.user, show=show)
    status = request.POST.get("status", "").strip()
    if status not in WatchlistItem.Status.values:
        return HttpResponseBadRequest("Choose a valid watchlist status.")
    try:
        season = _progress_value(request, "current_season")
        episode = _progress_value(request, "current_episode")
    except ValueError as error:
        return HttpResponseBadRequest(str(error))
    if episode is not None and season is None:
        return HttpResponseBadRequest("Add a season before saving an episode.")

    item.status = status
    if (item.current_season, item.current_episode) != (season, episode):
        item.current_episode_image_url = ""
    item.current_season = season
    item.current_episode = episode
    item.last_updated_at = timezone.now()
    item.save(update_fields=["status", "current_season", "current_episode", "current_episode_image_url", "last_updated_at"])
    return _watchlist_response(request, show, "updated", item)


@login_required
@require_POST
def set_episode_progress(request, slug):
    """Set the selected, verified episode as a member's current progress."""
    show = get_object_or_404(Show, slug=slug, status=Show.Status.PUBLISHED)
    try:
        season = _progress_value(request, "season")
        episode = _progress_value(request, "episode")
    except ValueError as error:
        return HttpResponseBadRequest(str(error))
    if season is None or episode is None:
        return HttpResponseBadRequest("Choose both a season and an episode.")
    if show.source_name != "TVmaze" or not show.source_id:
        return HttpResponseBadRequest("Episode tracking is unavailable for this show.")
    episodes = fetch_show_episodes(show.source_id)
    selected_episode = next((
        entry for entry in episodes
        if entry["season"] == season and entry["number"] == episode
    ), None)
    if selected_episode is None:
        return HttpResponseBadRequest("That episode is not available for this show.")

    item, _created = WatchlistItem.objects.get_or_create(user=request.user, show=show)
    item.status = WatchlistItem.Status.WATCHING
    item.current_season = season
    item.current_episode = episode
    item.current_episode_image_url = selected_episode["image_url"]
    item.last_updated_at = timezone.now()
    item.save(update_fields=["status", "current_season", "current_episode", "current_episode_image_url", "last_updated_at"])
    return _watchlist_response(request, show, "episode-set", item, episodes)


@login_required
@require_POST
def mark_episode_watched(request, slug):
    """Advance a member to the next TVMaze episode, or complete a finale."""
    show = get_object_or_404(Show, slug=slug, status=Show.Status.PUBLISHED)
    item = get_object_or_404(WatchlistItem, user=request.user, show=show)
    if not (show.source_name == "TVmaze" and show.source_id and item.current_season and item.current_episode):
        return HttpResponseBadRequest("Choose an episode before marking it watched.")
    episodes = fetch_show_episodes(show.source_id)
    current_index = next((
        index for index, entry in enumerate(episodes)
        if entry["season"] == item.current_season and entry["number"] == item.current_episode
    ), None)
    if current_index is None:
        return HttpResponseBadRequest("That episode is no longer available for this show.")

    next_episode = episodes[current_index + 1] if current_index + 1 < len(episodes) else None
    if next_episode is None:
        item.status = WatchlistItem.Status.COMPLETED
    else:
        item.current_season = next_episode["season"]
        item.current_episode = next_episode["number"]
        item.current_episode_image_url = next_episode["image_url"]
    item.last_updated_at = timezone.now()
    item.save(update_fields=["status", "current_season", "current_episode", "current_episode_image_url", "last_updated_at"])
    return _watchlist_response(request, show, "episode-watched", item, episodes)


@login_required
@require_POST
def import_to_watchlist(request, source_id):
    """Import one TVmaze match, then save it to the member's watchlist."""
    data = fetch_show(source_id)
    if data is None:
        return redirect("show-list")

    show, _created = upsert_show(data, publish=True)
    WatchlistItem.objects.get_or_create(user=request.user, show=show)
    return redirect(show)
