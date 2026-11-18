from django.db import migrations, models


def feature_existing_published_shows(apps, schema_editor):
    Show = apps.get_model("catalog", "Show")
    Show.objects.filter(status="published").update(featured_on_home=True)


class Migration(migrations.Migration):
    dependencies = [("catalog", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="show",
            name="featured_on_home",
            field=models.BooleanField(
                default=False,
                help_text="Show this published title in the curated homepage rows.",
            ),
        ),
        migrations.RunPython(feature_existing_published_shows, migrations.RunPython.noop),
    ]
