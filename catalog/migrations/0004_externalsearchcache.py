# Generated for WatchVault's shared external-search cache.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalog", "0003_show_title_trigram_index")]

    operations = [
        migrations.CreateModel(
            name="ExternalSearchCache",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("query", models.CharField(max_length=255, unique=True)),
                ("results", models.JSONField(default=list)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
