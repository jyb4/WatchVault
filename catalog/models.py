from django.conf import settings
from django.db import models
from django.urls import reverse


class Genre(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Show(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    synopsis = models.TextField(blank=True)
    poster_url = models.URLField(blank=True)
    premiered_on = models.DateField(null=True, blank=True)
    external_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    network = models.CharField(max_length=120, blank=True)
    genres = models.ManyToManyField(Genre, blank=True)
    source_name = models.CharField(max_length=100, blank=True, null=True)
    source_id = models.CharField(max_length=100, blank=True, null=True)
    source_url = models.URLField(blank=True)
    import_updated_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        constraints = [models.UniqueConstraint(fields=["source_name", "source_id"], name="unique_show_source")]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("show-detail", kwargs={"slug": self.slug})


class WatchlistItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watchlist_items")
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name="saved_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "show"], name="unique_watchlist_item")]
        ordering = ["-created_at"]
