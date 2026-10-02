"""Siembra el rol "Superusuario" por defecto: un `auth.Group` con el
catálogo completo de permisos asignado, para que cualquier clon de este
template tenga un rol administrativo completo listo de inmediato.

Deliberadamente sin usuarios ni contraseñas — ver docs/roles-and-permissions.md,
sección "AC-038", sobre por qué "administrador" real se define por
`is_superuser=True` y no por la sola pertenencia a este rol (este rol es un
agrupador de permisos útil para asignar a cualquier cuenta administrativa,
sea o no superusuario de Django)."""

from django.db import migrations

DEFAULT_ROLE_NAME = "Superusuario"


def seed_superusuario_role(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    # En una base nueva, Django crea ContentType y Permission recién en
    # `post_migrate` (después de todas las migraciones), así que aquí se
    # crean explícitamente si aún no existen, a partir del estado histórico
    # del modelo ancla.
    content_type, _ = ContentType.objects.get_or_create(
        app_label="permissions", model="modulepermission"
    )
    ModulePermission = apps.get_model("permissions", "ModulePermission")
    for codename, name in ModulePermission._meta.permissions:
        Permission.objects.get_or_create(
            content_type=content_type, codename=codename, defaults={"name": name}
        )
    group, _ = Group.objects.get_or_create(name=DEFAULT_ROLE_NAME)
    group.permissions.set(Permission.objects.filter(content_type=content_type))


def noop_reverse(apps, schema_editor):
    # No se elimina el rol al revertir: es configuración, no un dato
    # transaccional del que dependa la reversión del esquema.
    pass


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("permissions", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_superusuario_role, noop_reverse),
    ]
