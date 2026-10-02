"""El rol de una membresía pasa de texto fijo a un rol editable (`auth.Group`).

1. Crea los permisos `matriz.*`, `empresas.*` y `catalogos.*` si aún no
   existen (en una base nueva Django los crea recién en `post_migrate`).
2. Siembra los 4 roles por defecto con sus permisos, solo si no existen.
3. Convierte cada membresía de su texto ("responsable", …) al rol.
"""

import django.db.models.deletion
from django.db import migrations, models

from apps.organizations.default_roles import DEFAULT_ROLES, LEGACY_ROLE_NAMES


def seed_roles_and_convert(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    ModulePermission = apps.get_model("permissions", "ModulePermission")
    Membership = apps.get_model("organizations", "Membership")

    content_type, _ = ContentType.objects.get_or_create(
        app_label="permissions", model="modulepermission"
    )
    for codename, name in ModulePermission._meta.permissions:
        Permission.objects.get_or_create(
            content_type=content_type, codename=codename, defaults={"name": name}
        )

    groups = {}
    for name, codenames in DEFAULT_ROLES.items():
        group, created = Group.objects.get_or_create(name=name)
        if created:
            group.permissions.set(
                Permission.objects.filter(content_type=content_type, codename__in=codenames)
            )
        groups[name] = group

    for membership in Membership.objects.all():
        role_name = LEGACY_ROLE_NAMES.get(membership.legacy_role, "Auditor")
        membership.role = groups[role_name]
        membership.save(update_fields=["role"])


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("permissions", "0002_alter_modulepermission_options"),
        ("organizations", "0002_rename_site_theme"),
    ]

    operations = [
        migrations.RenameField("membership", "role", "legacy_role"),
        migrations.AddField(
            model_name="membership",
            name="role",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="memberships",
                to="auth.group",
            ),
        ),
        migrations.RunPython(seed_roles_and_convert, migrations.RunPython.noop),
        migrations.RemoveField("membership", "legacy_role"),
        migrations.AlterField(
            model_name="membership",
            name="role",
            field=models.ForeignKey(
                help_text="Rol del template base con los permisos matriz.* que tiene en esta empresa.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="memberships",
                to="auth.group",
            ),
        ),
    ]
