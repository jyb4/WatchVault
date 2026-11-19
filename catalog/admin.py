from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils import timezone
from .models import Genre, Show, WatchlistItem


class EditorialReviewFilter(SimpleListFilter):
    title = "editorial review"
    parameter_name = "review_queue"

    def lookups(self, request, model_admin):
        return (("ready", "Ready for review"), ("reviewed", "Previously reviewed"))

    def queryset(self, request, queryset):
        qualified = queryset.filter(
            status=Show.Status.PUBLISHED,
            poster_url__gt="",
            synopsis__gt="",
            external_rating__isnull=False,
        )
        if self.value() == "ready":
            return qualified.filter(editorial_reviewed_at__isnull=True)
        if self.value() == "reviewed":
            return qualified.filter(editorial_reviewed_at__isnull=False)
        return queryset


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = (
        "title", "status", "featured_on_home", "homepage_trending", "homepage_fresh",
        "editorial_priority", "editorial_reviewed_at", "network", "external_rating", "updated_at",
    )
    list_editable = ("featured_on_home", "homepage_trending", "homepage_fresh", "editorial_priority")
    list_filter = (EditorialReviewFilter, "status", "featured_on_home", "homepage_trending", "homepage_fresh", "genres", "network")
    search_fields = ("title", "synopsis", "network")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("genres",)
    readonly_fields = ("editorial_reviewed_at",)
    actions = ("mark_reviewed", "return_to_review_queue")
    fieldsets = (
        ("Show information", {"fields": ("title", "slug", "synopsis", "poster_url", "premiered_on", "external_rating", "network", "genres")}),
        ("Publishing", {"fields": ("status", "featured_on_home", "homepage_trending", "homepage_fresh", "editorial_priority", "editorial_reviewed_at")}),
        ("TVmaze source", {"fields": ("source_name", "source_id", "source_url", "import_updated_at")}),
    )

    def save_model(self, request, obj, form, change):
        placement_fields = {"featured_on_home", "homepage_trending", "homepage_fresh", "editorial_priority"}
        if change and placement_fields.intersection(form.changed_data):
            obj.editorial_reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)

    @admin.action(description="Mark selected shows as reviewed")
    def mark_reviewed(self, request, queryset):
        queryset.update(editorial_reviewed_at=timezone.now())

    @admin.action(description="Return selected shows to the review queue")
    def return_to_review_queue(self, request, queryset):
        queryset.update(editorial_reviewed_at=None)


admin.site.register(Genre)
admin.site.register(WatchlistItem)
