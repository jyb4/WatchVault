from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0008_watchlistitem_tracking"),
    ]

    operations = [
        migrations.AddField(
            model_name="watchlistitem",
            name="current_episode_image_url",
            field=models.URLField(blank=True),
        ),
    ]
