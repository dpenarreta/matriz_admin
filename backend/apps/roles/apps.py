from django.apps import AppConfig
from django.db.models.signals import post_migrate


class RolesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.roles"
    verbose_name = "Roles"

    def ready(self):
        from .signals import sync_superusuario_role

        post_migrate.connect(sync_superusuario_role, sender=self)
