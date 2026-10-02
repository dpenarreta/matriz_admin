"""Mantiene el rol "Superusuario" sincronizado con el catálogo completo.

La migración `0001_initial` lo siembra con el catálogo vigente en ese
momento; cada módulo de negocio que sume permisos al catálogo
(`apps.permissions.catalog`) quedaría fuera del rol si no se resincroniza.
Este receptor corre después de que Django crea los `Permission` faltantes
(`post_migrate` de `django.contrib.auth`, conectado antes por orden de
`INSTALLED_APPS`)."""

DEFAULT_ROLE_NAME = "Superusuario"


def sync_superusuario_role(sender, **kwargs):
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType

    from apps.permissions.models import ModulePermission

    content_type = ContentType.objects.get_for_model(ModulePermission)
    group, _ = Group.objects.get_or_create(name=DEFAULT_ROLE_NAME)
    group.permissions.add(*Permission.objects.filter(content_type=content_type))
