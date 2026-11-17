from django.contrib import admin
from .models import Genre, Show, WatchlistItem


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "network", "external_rating", "updated_at")
    list_filter = ("status", "genres", "network")
    search_fields = ("title", "synopsis", "network")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("genres",)


admin.site.register(Genre)
admin.site.register(WatchlistItem)
