from django.contrib import admin
from .models import Genre, Show, WatchlistItem


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = (
        "title", "status", "featured_on_home", "homepage_trending", "homepage_fresh",
        "editorial_priority", "network", "external_rating", "updated_at",
    )
    list_editable = ("featured_on_home", "homepage_trending", "homepage_fresh", "editorial_priority")
    list_filter = ("status", "featured_on_home", "homepage_trending", "homepage_fresh", "genres", "network")
    search_fields = ("title", "synopsis", "network")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("genres",)
    fieldsets = (
        ("Show information", {"fields": ("title", "slug", "synopsis", "poster_url", "premiered_on", "external_rating", "network", "genres")}),
        ("Publishing", {"fields": ("status", "featured_on_home", "homepage_trending", "homepage_fresh", "editorial_priority")}),
        ("TVmaze source", {"fields": ("source_name", "source_id", "source_url", "import_updated_at")}),
    )


admin.site.register(Genre)
admin.site.register(WatchlistItem)
