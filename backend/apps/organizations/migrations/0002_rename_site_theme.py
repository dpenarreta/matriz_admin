"""Renombra la identidad visual sembrada por el template base ("Skelleton
Base") a la de este proyecto. Solo toca el tema si nadie lo personalizó."""

from django.db import migrations

OLD_NAMES = {"Skelleton Base"}
NEW_NAME = "Matriz Administrativa de Obligaciones"


def rename(apps, schema_editor):
    SiteTheme = apps.get_model("branding", "SiteTheme")
    for theme in SiteTheme.objects.filter(site_name__in=OLD_NAMES):
        theme.site_name = NEW_NAME
        if hasattr(theme, "short_name"):
            theme.short_name = "Matriz"
        theme.save()


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0001_initial"),
        ("branding", "0002_seed_default_theme"),
    ]

    operations = [migrations.RunPython(rename, migrations.RunPython.noop)]
