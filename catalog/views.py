from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView
from .models import Show, WatchlistItem
from .tvmaze import fetch_show, search_shows as search_tvmaze_shows, upsert_show


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


def local_search(request):
    """Return catalog matches immediately, without waiting for an external service."""
    query = request.GET.get("q", "").strip()
    local_shows = Show.objects.filter(status=Show.Status.PUBLISHED)
    if query:
        local_shows = local_shows.filter(Q(title__icontains=query)).distinct()
    local_shows = local_shows.order_by("-external_rating", "title")[:8]
    return JsonResponse({"query": query, "results": [_search_result(show) for show in local_shows]})


def external_search(request):
    """Fetch supplemental TVmaze matches after the local catalog is already visible."""
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"query": query, "results": []})

    tvmaze_matches = search_tvmaze_shows(query)[:12]
    imported_ids = set(
        Show.objects.filter(
            status=Show.Status.PUBLISHED,
            source_name="TVmaze",
            source_id__in=[show["id"] for show in tvmaze_matches],
        ).values_list("source_id", flat=True)
    )
    results = [
        {
            "title": show["title"],
            "meta": "TVmaze match",
            "poster": show["poster_url"],
            "url": show["source_url"],
            "source": "TVmaze",
        }
        for show in tvmaze_matches
        if show["id"] not in imported_ids
    ]
    return JsonResponse({"query": query, "results": results[:12]})


class HomeView(ListView):
    template_name = "catalog/home.html"
    context_object_name = "featured_shows"

    def get_queryset(self):
        return Show.objects.filter(
            status=Show.Status.PUBLISHED,
            featured_on_home=True,
        ).prefetch_related("genres").order_by("-external_rating", "title")[:17]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shows = list(context["featured_shows"])
        context["hero_slides"] = shows[:5]
        context["trending"] = shows[:8]
        context["top_rated"] = shows[:6]
        context["recently_added"] = Show.objects.filter(
            status=Show.Status.PUBLISHED,
        ).prefetch_related("genres").order_by("-created_at")[:8]
        context["categories"] = Show.objects.filter(
            status=Show.Status.PUBLISHED,
        ).values_list("genres__name", flat=True).distinct().order_by("genres__name")[:8]
        context["watchlist_shows"] = []
        if self.request.user.is_authenticated:
            context["watchlist_shows"] = [
                item.show for item in WatchlistItem.objects.filter(user=self.request.user).select_related("show")[:8]
            ]
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
        context["saved"] = self.request.user.is_authenticated and WatchlistItem.objects.filter(
            user=self.request.user, show=self.object
        ).exists()
        return context


class WatchlistView(LoginRequiredMixin, ListView):
    template_name = "catalog/watchlist.html"
    context_object_name = "items"

    def get_queryset(self):
        return WatchlistItem.objects.filter(user=self.request.user).select_related("show")


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
    return redirect(show)


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
