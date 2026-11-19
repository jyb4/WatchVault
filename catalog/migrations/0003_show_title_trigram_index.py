from django.contrib.postgres.operations import TrigramExtension
from django.contrib.postgres.indexes import GinIndex
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_show_featured_on_home")]

    operations = [
        TrigramExtension(),
        migrations.AddIndex(
            model_name="show",
            index=GinIndex(fields=["title"], name="show_title_trgm_idx", opclasses=["gin_trgm_ops"]),
        ),
    ]
