"""Roles de negocio que se siembran por defecto (los del mockup).

Son roles normales del template base (`auth.Group`): se pueden editar,
renombrar o eliminar en Administración → Roles, y se pueden crear otros con
cualquier combinación de permisos `matriz.*`. Este módulo solo define el
punto de partida; nunca se vuelve a imponer después de la primera siembra.
"""

MATRIZ_ALL = [
    "matriz.ver_todas",
    "matriz.crear",
    "matriz.editar",
    "matriz.cambiar_fecha",
    "matriz.cargar",
    "matriz.enviar",
    "matriz.validar",
    "matriz.recordar",
    "matriz.exportar",
    "matriz.ver_auditoria",
    "matriz.configurar",
    "matriz.gestionar_miembros",
]

DEFAULT_ROLES = {
    "Administrador": MATRIZ_ALL,
    "Responsable": [
        "matriz.crear",
        "matriz.editar",
        "matriz.cargar",
        "matriz.enviar",
        "matriz.recordar",
    ],
    "Supervisor/Aprobador": [
        "matriz.ver_todas",
        "matriz.cambiar_fecha",
        "matriz.validar",
        "matriz.recordar",
        "matriz.exportar",
        "matriz.ver_auditoria",
    ],
    "Auditor": ["matriz.ver_todas", "matriz.exportar", "matriz.ver_auditoria"],
}

# Valor del antiguo campo de texto `Membership.role` -> nombre del rol.
LEGACY_ROLE_NAMES = {
    "administrador": "Administrador",
    "responsable": "Responsable",
    "supervisor": "Supervisor/Aprobador",
    "auditor": "Auditor",
}


class RoleName:
    """Nombres de los roles sembrados, para el código que los necesita por
    nombre (siembra de datos demo y pruebas)."""

    ADMIN = "Administrador"
    RESPONSIBLE = "Responsable"
    SUPERVISOR = "Supervisor/Aprobador"
    AUDITOR = "Auditor"


def default_role(name: str):
    from django.contrib.auth.models import Group

    return Group.objects.get(name=name)
