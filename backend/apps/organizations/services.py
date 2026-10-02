"""Lógica de negocio de empresas y membresías."""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.core.audit import record_audit_event
from apps.users.models import User

from .models import Area, Company, Membership

COMPANY_EDITABLE_FIELDS = (
    "legal_name",
    "short_name",
    "country",
    "activity",
    "timezone",
    "color",
    "compliance_date_basis",
    "general_manager",
)


def validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValidationError({"timezone": "Zona horaria IANA no válida."}) from exc
    return value


class CompanyService:
    @staticmethod
    def update_settings(*, actor: User, company: Company, context=None, **fields) -> Company:
        previous, new = {}, {}
        for name in COMPANY_EDITABLE_FIELDS:
            if name not in fields:
                continue
            value = fields[name]
            if name == "timezone":
                validate_timezone(value)
            current = getattr(company, name)
            if current != value:
                previous[name] = str(current) if current is not None else None
                new[name] = str(value) if value is not None else None
                setattr(company, name, value)
        if new:
            company.save()
            record_audit_event(
                actor=actor,
                action="company.updated",
                module="matriz",
                target=company,
                previous_values=previous,
                new_values=new,
                context=context,
            )
        return company


class MembershipService:
    @staticmethod
    def _active_admin_count(company: Company) -> int:
        return Membership.objects.filter(
            company=company, role=Membership.Role.ADMIN, is_active=True, user__is_active=True
        ).count()

    @staticmethod
    def _guard_last_admin(membership: Membership, *, new_role=None, deactivating=False) -> None:
        is_admin = membership.role == Membership.Role.ADMIN and membership.is_active
        loses_admin = deactivating or (new_role is not None and new_role != Membership.Role.ADMIN)
        if (
            is_admin
            and loses_admin
            and MembershipService._active_admin_count(membership.company) <= 1
        ):
            raise ValidationError(
                {"role": "No se puede quitar el último Administrador activo de la empresa."}
            )

    @staticmethod
    @transaction.atomic
    def add(
        *, actor: User, company: Company, user: User, role: str, areas: list[Area], context=None
    ) -> Membership:
        membership, created = Membership.objects.get_or_create(
            user=user, company=company, defaults={"role": role}
        )
        if not created:
            if membership.is_active:
                raise ValidationError({"user": "El usuario ya tiene un rol en esta empresa."})
            membership.is_active = True
            membership.role = role
            membership.save()
        membership.areas.set(areas)
        record_audit_event(
            actor=actor,
            action="membership.created",
            module="matriz",
            target=membership,
            new_values={
                "user": user.username,
                "company": company.code,
                "role": role,
                "areas": [area.code for area in areas],
            },
            context=context,
        )
        return membership

    @staticmethod
    @transaction.atomic
    def update(
        *, actor: User, membership: Membership, role=None, areas=None, context=None
    ) -> Membership:
        previous, new = {}, {}
        if role is not None and role != membership.role:
            MembershipService._guard_last_admin(membership, new_role=role)
            previous["role"], new["role"] = membership.role, role
            membership.role = role
            membership.save(update_fields=["role", "updated_at"])
        if areas is not None:
            before = sorted(area.code for area in membership.areas.all())
            after = sorted(area.code for area in areas)
            if before != after:
                previous["areas"], new["areas"] = before, after
            membership.areas.set(areas)
        if new:
            record_audit_event(
                actor=actor,
                action="membership.updated",
                module="matriz",
                target=membership,
                previous_values=previous,
                new_values=new,
                context=context,
            )
        return membership

    @staticmethod
    def deactivate(*, actor: User, membership: Membership, context=None) -> None:
        MembershipService._guard_last_admin(membership, deactivating=True)
        membership.is_active = False
        membership.save(update_fields=["is_active", "updated_at"])
        record_audit_event(
            actor=actor,
            action="membership.deactivated",
            module="matriz",
            target=membership,
            previous_values={"role": membership.role, "user": membership.user.username},
            context=context,
        )
