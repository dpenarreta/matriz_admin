"""Control de acceso de negocio por empresa (documento funcional, sección 4).

Lo que una persona puede hacer en una empresa son los permisos `matriz.*`
del rol de su membresía en esa empresa. Los roles son los del template base
(`auth.Group`): se crean y se editan en Administración → Roles, así que este
módulo no tiene ninguna lista fija de qué puede cada rol.

Regla de alcance: quien no tiene `matriz.ver_todas` solo ve y actúa sobre
los períodos donde es responsable o suplente (la segunda comprobación vive
en `apps.obligations.policies`, que conoce el modelo `Period`).

Un superusuario de Django tiene todos los permisos en todas las empresas,
igual que en el template base es el bypass total del catálogo.
"""

from dataclasses import dataclass, field

from django.contrib.auth.models import Group
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.core.audit import record_audit_event
from apps.core.models import AuditLog
from apps.permissions.catalog import PERMISSION_CATALOG

from .models import Company, Membership

MODULE = "matriz"
PREFIX = f"{MODULE}."


class Cap:
    """Capacidades: el codename del catálogo sin el prefijo `matriz.`.
    Constantes en vez de strings sueltos para que un error de tipeo falle al
    importar y no en producción."""

    VIEW_ALL = "ver_todas"
    CREATE = "crear"
    EDIT = "editar"
    CHANGE_DUE_DATE = "cambiar_fecha"
    UPLOAD = "cargar"
    SUBMIT = "enviar"
    VALIDATE = "validar"
    REMIND = "recordar"
    CONFIGURE = "configurar"
    MANAGE_MEMBERS = "gestionar_miembros"
    EXPORT = "exportar"
    VIEW_AUDIT = "ver_auditoria"


ALL_CAPABILITIES = frozenset(
    codename.removeprefix(PREFIX) for codename in PERMISSION_CATALOG[MODULE]["permissions"]
)

# Capacidades que se ejercen sobre un período concreto. Sin `ver_todas`,
# solo sobre los períodos propios.
PERIOD_SCOPED = frozenset(
    {
        Cap.EDIT,
        Cap.CHANGE_DUE_DATE,
        Cap.UPLOAD,
        Cap.SUBMIT,
        Cap.VALIDATE,
        Cap.REMIND,
    }
)


def role_capabilities(role: Group) -> frozenset[str]:
    """Permisos `matriz.*` del rol, sin el prefijo."""
    codenames = role.permissions.filter(codename__startswith=PREFIX).values_list(
        "codename", flat=True
    )
    return frozenset(codename.removeprefix(PREFIX) for codename in codenames)


def matrix_roles():
    """Roles que otorgan al menos un permiso de la matriz: los que tiene
    sentido asignar en una empresa."""
    return (
        Group.objects.filter(permissions__codename__startswith=PREFIX)
        .distinct()
        .prefetch_related("permissions")
        .order_by("name")
    )


@dataclass(frozen=True)
class CompanyAccess:
    """Lo que un usuario puede hacer en una empresa concreta."""

    company: Company
    role_id: int | None
    role_name: str
    capabilities: frozenset[str]
    area_ids: frozenset[int] = field(default_factory=frozenset)
    is_superuser: bool = False

    @property
    def sees_everything(self) -> bool:
        return Cap.VIEW_ALL in self.capabilities

    def has(self, capability: str) -> bool:
        return capability in self.capabilities

    def is_scoped(self, capability: str) -> bool:
        """True si la capacidad se limita a los períodos propios."""
        return not self.sees_everything and capability in PERIOD_SCOPED

    def can_create_in_area(self, area_id: int) -> bool:
        if not self.has(Cap.CREATE):
            return False
        if self.sees_everything or not self.area_ids:
            return True
        return area_id in self.area_ids


def get_access(user, company: Company) -> CompanyAccess | None:
    if user is None or not user.is_authenticated or not company.is_active:
        return None
    if user.is_superuser:
        return CompanyAccess(
            company=company,
            role_id=None,
            role_name="Superusuario",
            capabilities=ALL_CAPABILITIES,
            is_superuser=True,
        )
    membership = (
        Membership.objects.filter(user=user, company=company, is_active=True)
        .select_related("role")
        .prefetch_related("areas")
        .first()
    )
    if membership is None:
        return None
    return CompanyAccess(
        company=company,
        role_id=membership.role_id,
        role_name=membership.role.name,
        capabilities=role_capabilities(membership.role),
        area_ids=frozenset(area.id for area in membership.areas.all()),
    )


def accessible_companies(user):
    """Empresas activas donde el usuario tiene rol (todas, para un superusuario)."""
    queryset = Company.objects.filter(is_active=True)
    if user.is_superuser:
        return queryset
    return queryset.filter(memberships__user=user, memberships__is_active=True).distinct()


def deny(request, message: str, *, capability: str = "", target=None) -> None:
    """Registra el intento en la bitácora del template base y corta con 403."""
    if request is not None and request.user and request.user.is_authenticated:
        from apps.core.request_meta import get_request_context

        record_audit_event(
            actor=request.user,
            action="access_denied",
            module=MODULE,
            target=target if target is not None else request.user,
            new_values={
                "required_permission": f"{PREFIX}{capability}" if capability else "",
                "method": request.method,
                "path": request.path,
            },
            result=AuditLog.Result.FAILURE,
            context=get_request_context(request),
        )
    raise PermissionDenied(message)


def require_access(request, company: Company) -> CompanyAccess:
    """Membresía obligatoria. Sin rol en la empresa se responde 404 y no 403,
    para no revelar qué empresas existen."""
    access = get_access(request.user, company)
    if access is None:
        raise NotFound("Empresa no encontrada.")
    return access


def require_capability(request, company: Company, capability: str, message: str = ""):
    access = require_access(request, company)
    if not access.has(capability):
        deny(
            request,
            message or f"Su rol ({access.role_name}) no tiene el permiso {PREFIX}{capability}.",
            capability=capability,
        )
    return access
