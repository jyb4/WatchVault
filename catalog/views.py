from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView
from .models import Show, WatchlistItem


class HomeView(ListView):
    template_name = "catalog/home.html"
    context_object_name = "shows"

    def get_queryset(self):
        return Show.objects.filter(status=Show.Status.PUBLISHED).prefetch_related("genres")[:6]


class ShowListView(ListView):
    template_name = "catalog/show_list.html"
    context_object_name = "shows"

    def get_queryset(self):
        shows = Show.objects.filter(status=Show.Status.PUBLISHED).prefetch_related("genres")
        query = self.request.GET.get("q", "").strip()
        if query:
            shows = shows.filter(title__icontains=query)
        return shows


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
