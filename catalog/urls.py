from django.urls import path
from . import views

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("shows/", views.ShowListView.as_view(), name="show-list"),
    path("shows/<slug:slug>/", views.ShowDetailView.as_view(), name="show-detail"),
    path("my-watchlist/", views.WatchlistView.as_view(), name="watchlist"),
    path("shows/<slug:slug>/watchlist/", views.add_to_watchlist, name="watchlist-add"),
    path("shows/<slug:slug>/watchlist/remove/", views.remove_from_watchlist, name="watchlist-remove"),
    path("shows/import/<int:source_id>/watchlist/", views.import_to_watchlist, name="tvmaze-import-watchlist"),
]
