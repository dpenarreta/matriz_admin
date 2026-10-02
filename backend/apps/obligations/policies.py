"""Reglas de acceso a nivel de período (documento funcional, sección 4).

`apps.organizations.access` decide qué puede hacer un rol en una empresa;
aquí se agrega la segunda condición: que el período sea "propio"
(responsable o suplente) cuando la capacidad está limitada a lo propio.
"""

from rest_framework.exceptions import NotFound

from apps.organizations.access import PREFIX, Cap, CompanyAccess, deny, get_access

from .models import Period


def is_owner(user, period: Period) -> bool:
    return user.pk in (period.responsible_id, period.backup_id)


def visible_periods(access: CompanyAccess, user):
    """Períodos que el usuario puede ver en la empresa: todos para los roles
    con `ver_todas`; solo los propios para el Responsable."""
    queryset = Period.objects.filter(company=access.company)
    if access.sees_everything:
        return queryset
    from django.db.models import Q

    return queryset.filter(Q(responsible=user) | Q(backup=user))


def access_for_period(request, period: Period) -> CompanyAccess:
    """Membresía en la empresa del período y visibilidad del período. Si no
    lo puede ver, 404 (no se revela que existe)."""
    access = get_access(request.user, period.company)
    if access is None or (not access.sees_everything and not is_owner(request.user, period)):
        raise NotFound("Período no encontrado.")
    return access


def require_period_capability(request, period: Period, capability: str, message: str = ""):
    access = access_for_period(request, period)
    if not access.has(capability):
        deny(
            request,
            message or f"Su rol ({access.role_name}) no tiene el permiso {PREFIX}{capability}.",
            capability=capability,
            target=period,
        )
    if access.is_scoped(capability) and not is_owner(request.user, period):
        deny(
            request,
            "Sin permisos: esta obligación no está asignada a su usuario ni a su suplente.",
            capability=capability,
            target=period,
        )
    return access


def period_actions(access: CompanyAccess, user, period: Period) -> dict:
    """Qué botones del detalle puede usar el usuario en este período. Es
    información para la interfaz; cada endpoint vuelve a comprobarlo."""

    def allowed(capability: str) -> bool:
        if not access.has(capability):
            return False
        return not access.is_scoped(capability) or is_owner(user, period)

    open_ = not period.is_closed
    pending = period.stage == Period.Stage.PENDING_VALIDATION
    return {
        "edit": open_ and allowed(Cap.EDIT),
        "change_due_date": open_ and allowed(Cap.CHANGE_DUE_DATE),
        "upload": open_ and allowed(Cap.UPLOAD),
        "submit": open_ and not pending and allowed(Cap.SUBMIT),
        "validate": open_ and pending and allowed(Cap.VALIDATE),
        "return": open_ and pending and allowed(Cap.VALIDATE),
        "reject_document": open_ and allowed(Cap.VALIDATE),
        "remind": open_ and not period.reminders_suspended and allowed(Cap.REMIND),
    }
