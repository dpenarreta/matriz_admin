"""Lógica de negocio de empresas, catálogos y membresías."""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import transaction
from django.db.models import ProtectedError
from rest_framework.exceptions import ValidationError

from apps.core.audit import record_audit_event
from apps.users.models import User

from .access import PREFIX, Cap
from .models import Area, Branch, Company, ControlEntity, Membership

COMPANY_EDITABLE_FIELDS = (
    "code",
    "legal_name",
    "short_name",
    "country",
    "activity",
    "timezone",
    "color",
    "compliance_date_basis",
    "general_manager",
    "is_active",
)


def validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValidationError({"timezone": "Zona horaria IANA no válida."}) from exc
    return value


def _changes(instance, fields: dict, allowed) -> tuple[dict, dict]:
    previous, new = {}, {}
    for name in allowed:
        if name not in fields:
            continue
        value, current = fields[name], getattr(instance, name)
        if current != value:
            previous[name] = str(current) if current is not None else None
            new[name] = str(value) if value is not None else None
            setattr(instance, name, value)
    return previous, new


class CompanyService:
    @staticmethod
    @transaction.atomic
    def create(
        *, actor: User, context=None, branches: list[str] | None = None, **fields
    ) -> Company:
        if "timezone" in fields:
            validate_timezone(fields["timezone"])
        if Company.objects.filter(code__iexact=fields["code"]).exists():
            raise ValidationError({"code": "Ya existe una empresa con ese código."})
        company = Company.objects.create(**fields)
        for name in branches or []:
            Branch.objects.create(company=company, name=name)
        record_audit_event(
            actor=actor,
            action="company.created",
            module="empresas",
            target=company,
            new_values={"code": company.code, "legal_name": company.legal_name},
            context=context,
        )
        return company

    @staticmethod
    def update_settings(*, actor: User, company: Company, context=None, **fields) -> Company:
        if "timezone" in fields:
            validate_timezone(fields["timezone"])
        if "code" in fields and (
            Company.objects.filter(code__iexact=fields["code"]).exclude(pk=company.pk).exists()
        ):
            raise ValidationError({"code": "Ya existe una empresa con ese código."})
        previous, new = _changes(company, fields, COMPANY_EDITABLE_FIELDS)
        if new:
            company.save()
            record_audit_event(
                actor=actor,
                action="company.updated",
                module="empresas",
                target=company,
                previous_values=previous,
                new_values=new,
                context=context,
            )
        return company


class BranchService:
    @staticmethod
    def save(*, actor: User, company: Company, branch: Branch | None, context=None, **fields):
        name = fields.get("name", branch.name if branch else "").strip()
        duplicate = Branch.objects.filter(company=company, name__iexact=name)
        if branch is not None:
            duplicate = duplicate.exclude(pk=branch.pk)
        if duplicate.exists():
            raise ValidationError({"name": "Ya existe una sucursal con ese nombre."})
        if branch is None:
            branch = Branch.objects.create(company=company, **{**fields, "name": name})
            previous, new = {}, {"name": name}
        else:
            previous, new = _changes(branch, {**fields, "name": name}, ("name", "is_active"))
            branch.save()
        if new:
            record_audit_event(
                actor=actor,
                action="branch.saved",
                module="empresas",
                target=branch,
                previous_values=previous,
                new_values=new,
                context=context,
            )
        return branch


class CatalogService:
    """Áreas y entidades de control (catálogos compartidos)."""

    @staticmethod
    def save(*, actor: User, model, instance=None, context=None, **fields):
        code = fields.get("code", instance.code if instance else "").strip().upper()
        duplicate = model.objects.filter(code__iexact=code)
        if instance is not None:
            duplicate = duplicate.exclude(pk=instance.pk)
        if duplicate.exists():
            raise ValidationError({"code": "Ya existe un registro con ese código."})
        fields = {**fields, "code": code}
        if instance is None:
            instance = model.objects.create(**fields)
            previous, new = {}, fields
        else:
            previous, new = _changes(instance, fields, ("code", "name"))
            instance.save()
        if new:
            record_audit_event(
                actor=actor,
                action=f"{model.__name__.lower()}.saved",
                module="catalogos",
                target=instance,
                previous_values=previous,
                new_values=new,
                context=context,
            )
        return instance

    @staticmethod
    def delete(*, actor: User, instance, context=None) -> None:
        label = f"{instance.code} — {instance.name}"
        model_name = instance.__class__.__name__.lower()
        pk = instance.pk
        try:
            instance.delete()
        except ProtectedError as exc:
            raise ValidationError(
                {"detail": "No se puede eliminar: hay obligaciones que lo usan."}
            ) from exc
        record_audit_event(
            actor=actor,
            action=f"{model_name}.deleted",
            module="catalogos",
            target_type=model_name,
            target_id=pk,
            previous_values={"value": label},
            context=context,
        )


CATALOG_MODELS = {"areas": Area, "control-entities": ControlEntity}


class MembershipService:
    MANAGER_PERMISSION = f"{PREFIX}{Cap.MANAGE_MEMBERS}"

    @staticmethod
    def _is_manager_role(role) -> bool:
        return role.permissions.filter(codename=MembershipService.MANAGER_PERMISSION).exists()

    @staticmethod
    def _active_manager_count(company: Company) -> int:
        return (
            Membership.objects.filter(
                company=company,
                is_active=True,
                user__is_active=True,
                role__permissions__codename=MembershipService.MANAGER_PERMISSION,
            )
            .distinct()
            .count()
        )

    @staticmethod
    def _guard_last_admin(membership: Membership, *, new_role=None, deactivating=False) -> None:
        """La empresa nunca queda sin alguien que pueda gestionar sus roles
        (equivalente por empresa al "último administrador" del template base)."""
        is_manager = membership.is_active and MembershipService._is_manager_role(membership.role)
        loses = deactivating or (
            new_role is not None and not MembershipService._is_manager_role(new_role)
        )
        if (
            is_manager
            and loses
            and MembershipService._active_manager_count(membership.company) <= 1
        ):
            raise ValidationError(
                {
                    "role_id": "No se puede quitar a la última persona que gestiona los roles "
                    "de la empresa."
                }
            )

    @staticmethod
    @transaction.atomic
    def add(*, actor: User, company: Company, user: User, role, areas: list[Area], context=None):
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
                "role": role.name,
                "areas": [area.code for area in areas],
            },
            context=context,
        )
        return membership

    @staticmethod
    @transaction.atomic
    def update(*, actor: User, membership: Membership, role=None, areas=None, context=None):
        previous, new = {}, {}
        if role is not None and role.pk != membership.role_id:
            MembershipService._guard_last_admin(membership, new_role=role)
            previous["role"], new["role"] = membership.role.name, role.name
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
            previous_values={"role": membership.role.name, "user": membership.user.username},
            context=context,
        )

    @staticmethod
    @transaction.atomic
    def replace_for_user(*, actor: User, user: User, entries: list[dict], context=None):
        """Deja al usuario exactamente con las membresías de `entries`
        (`company`, `role`, `areas`): crea, actualiza o desactiva las demás.
        Lo usa el formulario de usuario de Administración del sistema."""
        wanted = {entry["company"].pk: entry for entry in entries}
        current = {m.company_id: m for m in user.memberships.select_related("company", "role")}
        for company_id, membership in current.items():
            if company_id not in wanted and membership.is_active:
                MembershipService.deactivate(actor=actor, membership=membership, context=context)
        for company_id, entry in wanted.items():
            membership = current.get(company_id)
            if membership is None or not membership.is_active:
                MembershipService.add(
                    actor=actor,
                    company=entry["company"],
                    user=user,
                    role=entry["role"],
                    areas=entry.get("areas", []),
                    context=context,
                )
            else:
                MembershipService.update(
                    actor=actor,
                    membership=membership,
                    role=entry["role"],
                    areas=entry.get("areas", []),
                    context=context,
                )
        return list(
            user.memberships.filter(is_active=True)
            .select_related("company", "role")
            .prefetch_related("areas")
        )
