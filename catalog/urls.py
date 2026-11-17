from django.urls import path
from . import views

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("shows/", views.ShowListView.as_view(), name="show-list"),
    path("shows/<slug:slug>/", views.ShowDetailView.as_view(), name="show-detail"),
    path("my-watchlist/", views.WatchlistView.as_view(), name="watchlist"),
]
