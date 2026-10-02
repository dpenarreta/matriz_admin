"""Control de acceso de negocio por empresa (documento funcional, sección 4).

Toda vista de la matriz resuelve primero la membresía del usuario en la
empresa del recurso y después pregunta por una *capacidad*. Las capacidades
"propias" (marcadas en `OWN_SCOPED`) además exigen que el usuario sea
responsable o suplente del período — esa segunda comprobación vive en
`apps.obligations.policies`, que conoce el modelo `Period`.

Un superusuario de Django se trata como Administrador en todas las
empresas, igual que en el template base es el bypass total del catálogo.
"""

from dataclasses import dataclass, field

from rest_framework.exceptions import NotFound, PermissionDenied

from apps.core.audit import record_audit_event
from apps.core.models import AuditLog

from .models import Company, Membership

Role = Membership.Role


class Cap:
    """Nombres de capacidades. Constantes en vez de strings sueltos para que
    un error de tipeo falle al importar y no en producción."""

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


ROLE_CAPABILITIES: dict[str, frozenset[str]] = {
    Role.ADMIN: frozenset(
        {
            Cap.VIEW_ALL,
            Cap.CREATE,
            Cap.EDIT,
            Cap.CHANGE_DUE_DATE,
            Cap.UPLOAD,
            Cap.SUBMIT,
            Cap.VALIDATE,
            Cap.REMIND,
            Cap.CONFIGURE,
            Cap.MANAGE_MEMBERS,
            Cap.EXPORT,
            Cap.VIEW_AUDIT,
        }
    ),
    Role.RESPONSIBLE: frozenset({Cap.CREATE, Cap.EDIT, Cap.UPLOAD, Cap.SUBMIT, Cap.REMIND}),
    Role.SUPERVISOR: frozenset(
        {Cap.VIEW_ALL, Cap.CHANGE_DUE_DATE, Cap.VALIDATE, Cap.REMIND, Cap.EXPORT, Cap.VIEW_AUDIT}
    ),
    Role.AUDITOR: frozenset({Cap.VIEW_ALL, Cap.EXPORT, Cap.VIEW_AUDIT}),
}

# Capacidades que el Responsable solo ejerce sobre sus propios períodos.
OWN_SCOPED = frozenset({Cap.EDIT, Cap.UPLOAD, Cap.SUBMIT, Cap.REMIND})


@dataclass(frozen=True)
class CompanyAccess:
    """Lo que un usuario puede hacer en una empresa concreta."""

    company: Company
    role: str
    area_ids: frozenset[int] = field(default_factory=frozenset)
    is_superuser: bool = False

    @property
    def capabilities(self) -> frozenset[str]:
        return ROLE_CAPABILITIES.get(self.role, frozenset())

    @property
    def sees_everything(self) -> bool:
        return Cap.VIEW_ALL in self.capabilities

    def has(self, capability: str) -> bool:
        return capability in self.capabilities

    def is_scoped(self, capability: str) -> bool:
        """True si la capacidad se limita a los períodos propios."""
        return self.role == Role.RESPONSIBLE and capability in OWN_SCOPED

    def can_create_in_area(self, area_id: int) -> bool:
        if not self.has(Cap.CREATE):
            return False
        if self.role != Role.RESPONSIBLE or not self.area_ids:
            return True
        return area_id in self.area_ids


def get_access(user, company: Company) -> CompanyAccess | None:
    if user is None or not user.is_authenticated or not company.is_active:
        return None
    if user.is_superuser:
        return CompanyAccess(company=company, role=Role.ADMIN, is_superuser=True)
    membership = (
        Membership.objects.filter(user=user, company=company, is_active=True)
        .prefetch_related("areas")
        .first()
    )
    if membership is None:
        return None
    return CompanyAccess(
        company=company,
        role=membership.role,
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
            module="matriz",
            target=target if target is not None else request.user,
            new_values={"capability": capability, "method": request.method, "path": request.path},
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
            message or f"Su rol ({access_role_label(access.role)}) no permite esta acción.",
            capability=capability,
        )
    return access


def access_role_label(role: str) -> str:
    return dict(Role.choices).get(role, role)
