from django.apps import AppConfig, apps
from django.db.models.signals import post_migrate


class RolesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.roles"
    verbose_name = "Roles"

    def ready(self):
        from .signals import sync_superusuario_role

        # Django emite post_migrate solo para apps con modelos, y esta no
        # tiene: se engancha a `permissions`, dueña del catálogo. El receptor
        # de auth que crea los Permission faltantes se conectó antes (orden
        # de INSTALLED_APPS), así que ya existen cuando corre este.
        post_migrate.connect(
            sync_superusuario_role,
            sender=apps.get_app_config("permissions"),
            dispatch_uid="sync_superusuario_role",
        )
