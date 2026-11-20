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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shows = list(context["featured_shows"])
        context["hero_slides"] = shows[:5]
        homepage_ready = self._homepage_ready()
        trending = homepage_ready.filter(homepage_trending=True).order_by(
            "-editorial_priority", F("external_rating").desc(nulls_last=True), "title"
        )
        context["trending"] = trending[:10] if trending.exists() else shows[:10]
        context["top_rated"] = homepage_ready.order_by(F("external_rating").desc(nulls_last=True), "title")[:15]
        pinned_fresh = list(homepage_ready.filter(homepage_fresh=True).order_by(
            "-editorial_priority", "-import_updated_at", "title"
        )[:14])
        automatic_fresh = homepage_ready.exclude(pk__in=[show.pk for show in pinned_fresh]).filter(
            external_rating__isnull=False,
        ).order_by("-import_updated_at", "-created_at")
        fresh = (pinned_fresh + list(automatic_fresh[:max(0, 14 - len(pinned_fresh))]))[:14]
        context["recently_added"] = fresh[:7]
        context["fresh_this_week"] = fresh[7:14]
        context["categories"] = Show.objects.filter(
            status=Show.Status.PUBLISHED,
        ).values_list("genres__name", flat=True).distinct().order_by("genres__name")[:8]
        context["continue_watching_items"] = []
        if self.request.user.is_authenticated:
            context["continue_watching_items"] = WatchlistItem.objects.filter(
                user=self.request.user,
                status=WatchlistItem.Status.WATCHING,
            ).select_related("show").prefetch_related("show__genres").order_by("-last_updated_at")[:8]
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
        context["watchlist_statuses"] = WatchlistItem.Status.choices
        return context


@login_required
@require_POST
def add_to_watchlist(request, slug):
    show = get_object_or_404(Show, slug=slug, status=Show.Status.PUBLISHED)
    WatchlistItem.objects.get_or_create(user=request.user, show=show)
    return redirect(show)


@login_required
@require_POST
def remove_from_watchlist(request, slug):
    show = get_object_or_404(Show, slug=slug, status=Show.Status.PUBLISHED)
    WatchlistItem.objects.filter(user=request.user, show=show).delete()
    return _watchlist_redirect(request, show)


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
    item.current_season = season
    item.current_episode = episode
    item.last_updated_at = timezone.now()
    item.save(update_fields=["status", "current_season", "current_episode", "last_updated_at"])
    return _watchlist_redirect(request, show)


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
    exists = any(
        entry["season"] == season and entry["number"] == episode
        for entry in fetch_show_episodes(show.source_id)
    )
    if not exists:
        return HttpResponseBadRequest("That episode is not available for this show.")

    item, _created = WatchlistItem.objects.get_or_create(user=request.user, show=show)
    item.status = WatchlistItem.Status.WATCHING
    item.current_season = season
    item.current_episode = episode
    item.last_updated_at = timezone.now()
    item.save(update_fields=["status", "current_season", "current_episode", "last_updated_at"])
    return _watchlist_redirect(request, show)


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
