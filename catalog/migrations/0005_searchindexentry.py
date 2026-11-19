from django.contrib.postgres.indexes import GinIndex
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalog", "0004_externalsearchcache")]

    operations = [
        migrations.CreateModel(
            name="SearchIndexEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_name", models.CharField(max_length=100)),
                ("source_id", models.CharField(max_length=100)),
                ("title", models.CharField(max_length=255)),
                ("aliases", models.JSONField(blank=True, default=list)),
                ("poster_url", models.URLField(blank=True)),
                ("source_url", models.URLField(blank=True)),
                ("external_rating", models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True)),
                ("popularity_boost", models.PositiveIntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddConstraint(
            model_name="searchindexentry",
            constraint=models.UniqueConstraint(fields=("source_name", "source_id"), name="unique_search_index_source"),
        ),
        migrations.AddIndex(
            model_name="searchindexentry",
            index=GinIndex(fields=["title"], name="search_index_title_trgm_idx", opclasses=["gin_trgm_ops"]),
        ),
    ]
