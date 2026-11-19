# Generated for the WatchVault per-user tracking milestone.
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0007_show_editorial_reviewed_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="watchlistitem",
            name="current_episode",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="watchlistitem",
            name="current_season",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="watchlistitem",
            name="last_updated_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name="watchlistitem",
            name="status",
            field=models.CharField(choices=[("plan", "Plan to Watch"), ("watching", "Watching"), ("completed", "Completed"), ("dropped", "Dropped")], default="plan", max_length=12),
        ),
        migrations.AlterModelOptions(
            name="watchlistitem",
            options={"ordering": ["-last_updated_at", "-created_at"]},
        ),
    ]
