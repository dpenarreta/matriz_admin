"""Empresas (tableros), sucursales, catálogos y membresías por empresa.

El rol de negocio de un usuario (Administrador, Responsable,
Supervisor/Aprobador, Auditor) vive en `Membership` y es **por empresa**:
la misma persona puede ser Responsable en una empresa y Auditor en otra.
Es independiente de los roles/permisos administrativos del template base
(`auth.Group` + catálogo de `apps.permissions`), que siguen gobernando el
panel `/admin` (usuarios, roles, auditoría técnica, identidad visual).
"""

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

from apps.core.models import BaseModel

HEX_COLOR_VALIDATOR = RegexValidator(
    regex=r"^#[0-9a-fA-F]{6}$", message="El color debe tener el formato #RRGGBB."
)


class Company(BaseModel):
    class ComplianceDateBasis(models.TextChoices):
        # Qué fecha cuenta como "cumplimiento" al validar un cierre (ver
        # documento funcional, sección 6.2). Por defecto, la de validación,
        # que es el comportamiento del mockup.
        VALIDATION = "validation", "Fecha de validación"
        SUBMISSION = "submission", "Fecha de envío a validación"

    code = models.CharField(max_length=10, unique=True)
    legal_name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=80)
    country = models.CharField(max_length=80, default="Ecuador")
    activity = models.CharField(max_length=255, blank=True)
    timezone = models.CharField(max_length=64, default="America/Guayaquil")
    color = models.CharField(max_length=7, default="#164b86", validators=[HEX_COLOR_VALIDATOR])
    general_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_companies",
        help_text="Aprobador por defecto de los períodos de la empresa.",
    )
    compliance_date_basis = models.CharField(
        max_length=20, choices=ComplianceDateBasis.choices, default=ComplianceDateBasis.VALIDATION
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["short_name"]
        verbose_name = "empresa"

    def __str__(self) -> str:
        return self.short_name


class Branch(BaseModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "sucursal"
        verbose_name_plural = "sucursales"
        constraints = [
            models.UniqueConstraint(fields=["company", "name"], name="uniq_branch_company_name")
        ]

    def __str__(self) -> str:
        return f"{self.company.short_name} — {self.name}"


class Area(BaseModel):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ["name"]
        verbose_name = "área"

    def __str__(self) -> str:
        return self.name


class ControlEntity(BaseModel):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=160)

    class Meta:
        ordering = ["name"]
        verbose_name = "entidad de control"
        verbose_name_plural = "entidades de control"

    def __str__(self) -> str:
        return self.name


class Membership(BaseModel):
    class Role(models.TextChoices):
        ADMIN = "administrador", "Administrador"
        RESPONSIBLE = "responsable", "Responsable"
        SUPERVISOR = "supervisor", "Supervisor/Aprobador"
        AUDITOR = "auditor", "Auditor"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=20, choices=Role.choices)
    # Solo relevante para el Responsable: áreas en las que puede crear
    # obligaciones. Vacío = cualquier área.
    areas = models.ManyToManyField(Area, blank=True, related_name="memberships")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company__short_name", "user__username"]
        verbose_name = "membresía"
        constraints = [
            models.UniqueConstraint(fields=["user", "company"], name="uniq_membership_user_company")
        ]

    def __str__(self) -> str:
        return f"{self.user} · {self.company} · {self.get_role_display()}"
