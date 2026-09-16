from django.db import migrations

DEFAULTS = [
    {"order": 0, "value": "95", "suffix": "%", "description": "learn more consistently with guided AI practice"},
    {"order": 1, "value": "5000", "suffix": "+", "description": "learners found clarity through mentorship"},
    {"order": 2, "value": "85", "suffix": "%", "description": "reported stronger interview confidence"},
]


def seed(apps, schema_editor):
    MarketingStat = apps.get_model("core", "MarketingStat")
    if not MarketingStat.objects.exists():
        MarketingStat.objects.bulk_create(MarketingStat(**d) for d in DEFAULTS)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_site_settings_and_marketing_stats"),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
