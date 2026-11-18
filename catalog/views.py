from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
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
        context["featured"] = shows[0] if shows else None
        context["trending"] = shows[1:9]
        context["more_to_explore"] = shows[9:17]
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
