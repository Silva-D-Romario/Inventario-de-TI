from django.db import migrations

DEFAULT_STATUSES = (
    {"code": "available", "name": "Disponível", "color": "#22C55E"},
    {"code": "in-use", "name": "Em uso", "color": "#3B82F6"},
    {"code": "maintenance", "name": "Em manutenção", "color": "#F59E0B"},
    {"code": "retired", "name": "Baixado", "color": "#64748B"},
)


def seed_asset_statuses(apps, schema_editor):
    asset_status = apps.get_model("inventory", "AssetStatus")
    for values in DEFAULT_STATUSES:
        asset_status.objects.get_or_create(code=values["code"], defaults=values)


class Migration(migrations.Migration):
    dependencies = [("inventory", "0001_initial")]

    operations = [
        migrations.RunPython(seed_asset_statuses, reverse_code=migrations.RunPython.noop),
    ]
