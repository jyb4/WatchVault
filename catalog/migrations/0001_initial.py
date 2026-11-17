# Generated as the initial WatchVault catalog schema.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Genre",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80, unique=True)),
                ("slug", models.SlugField(unique=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Show",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("slug", models.SlugField(unique=True)),
                ("synopsis", models.TextField(blank=True)),
                ("poster_url", models.URLField(blank=True)),
                ("premiered_on", models.DateField(blank=True, null=True)),
                ("external_rating", models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True)),
                ("network", models.CharField(blank=True, max_length=120)),
                ("source_name", models.CharField(blank=True, max_length=100, null=True)),
                ("source_id", models.CharField(blank=True, max_length=100, null=True)),
                ("source_url", models.URLField(blank=True)),
                ("import_updated_at", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("published", "Published")], default="draft", max_length=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("genres", models.ManyToManyField(blank=True, to="catalog.genre")),
            ],
            options={"ordering": ["title"]},
        ),
        migrations.CreateModel(
            name="WatchlistItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("show", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_by", to="catalog.show")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="watchlist_items", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="show",
            constraint=models.UniqueConstraint(fields=("source_name", "source_id"), name="unique_show_source"),
        ),
        migrations.AddConstraint(
            model_name="watchlistitem",
            constraint=models.UniqueConstraint(fields=("user", "show"), name="unique_watchlist_item"),
        ),
    ]
