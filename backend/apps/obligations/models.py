"""Obligaciones (plantillas recurrentes), sus períodos, evidencias e historial.

Separación clave (documento funcional, sección 3): una `Obligation` define
*qué* hay que cumplir y cada `Period` es *un* vencimiento concreto, con su
propia fecha, responsables, evidencia, etapa e historial. El estado
(Incumplido / En progreso / Finalizado) **no se guarda**: se calcula en
`apps.obligations.status` a partir de `is_closed`, `due_at` y la hora
actual en la zona horaria de la empresa.
"""

from datetime import time

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import BaseModel
from apps.organizations.models import Area, Branch, Company, ControlEntity


class Priority(models.TextChoices):
    HIGH = "alta", "Alta"
    MEDIUM = "media", "Media"
    LOW = "baja", "Baja"


PRIORITY_ORDER = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}


class Obligation(BaseModel):
    class Type(models.TextChoices):
        REGULATORY = "regulatoria", "Regulatoria"
        CONTRACTUAL = "contractual", "Contractual"
        INTERNAL = "interna", "Interna"

    class Periodicity(models.TextChoices):
        MONTHLY = "mensual", "Mensual"
        QUARTERLY = "trimestral", "Trimestral"
        SEMIANNUAL = "semestral", "Semestral"
        ANNUAL = "anual", "Anual"
        ONCE = "unica", "Única"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="obligations")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name="obligations")
    control_entity = models.ForeignKey(
        ControlEntity, on_delete=models.PROTECT, related_name="obligations"
    )
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.REGULATORY)
    periodicity = models.CharField(
        max_length=20, choices=Periodicity.choices, default=Periodicity.ANNUAL
    )
    legal_basis = models.TextField(blank=True)
    legal_basis_url = models.URLField(max_length=500, blank=True)
    expected_evidence = models.CharField(max_length=255)
    # Regla de vencimiento para generar los períodos siguientes (sección 6.5).
    # `due_day`: día del mes (se ajusta al último día si el mes es más corto).
    # `due_month`: mes del vencimiento para la periodicidad anual.
    due_day = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(31)]
    )
    due_month = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    due_time = models.TimeField(default=time(17, 0))
    default_priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_obligations",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "obligación"
        verbose_name_plural = "obligaciones"
        constraints = [
            models.UniqueConstraint(fields=["company", "name"], name="uniq_obligation_company_name")
        ]

    def __str__(self) -> str:
        return f"{self.company.code} · {self.name}"


class CodeSequence(models.Model):
    """Contador transaccional para códigos legibles (`OBL-0001`). Se bloquea
    la fila con `select_for_update` al generar, así dos altas simultáneas
    nunca repiten código (defecto 20 del mockup)."""

    name = models.CharField(max_length=30, unique=True)
    last_value = models.PositiveIntegerField(default=0)


class Period(BaseModel):
    class Stage(models.TextChoices):
        NOT_STARTED = "sin_iniciar", "Sin iniciar"
        IN_PREPARATION = "en_preparacion", "En preparación"
        PENDING_VALIDATION = "pendiente_validacion", "Pendiente de validación"

    code = models.CharField(max_length=20, unique=True)
    obligation = models.ForeignKey(Obligation, on_delete=models.PROTECT, related_name="periods")
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="periods")
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="periods"
    )
    label = models.CharField(max_length=60)
    start_date = models.DateField()
    preparation_date = models.DateField()
    due_at = models.DateTimeField(db_index=True)

    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="responsible_periods"
    )
    backup = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="backup_periods",
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supervised_periods",
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_periods",
    )

    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    progress = models.PositiveSmallIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    stage = models.CharField(max_length=30, choices=Stage.choices, default=Stage.NOT_STARTED)
    notes = models.TextField(blank=True)

    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_periods",
    )
    is_closed = models.BooleanField(default=False, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_periods",
    )
    reminders_suspended = models.BooleanField(default=False)

    class Meta:
        ordering = ["due_at"]
        verbose_name = "período"
        constraints = [
            models.UniqueConstraint(fields=["obligation", "label"], name="uniq_period_label")
        ]
        indexes = [models.Index(fields=["company", "is_closed", "due_at"])]

    def __str__(self) -> str:
        return f"{self.code} · {self.obligation.name} · {self.label}"


def document_upload_path(instance: "Document", filename: str) -> str:
    period = instance.period
    return (
        f"evidencias/{period.company.code}/{period.due_at:%Y}/{period.code}/"
        f"v{instance.version}-{instance.sha256[:12]}.pdf"
    )


class Document(BaseModel):
    class Status(models.TextChoices):
        VALID = "valido", "Válido"
        REJECTED = "rechazado", "Rechazado"
        DELETED = "eliminado", "Eliminado"

    period = models.ForeignKey(Period, on_delete=models.PROTECT, related_name="documents")
    file = models.FileField(upload_to=document_upload_path, max_length=300)
    original_name = models.CharField(max_length=255)
    version = models.PositiveIntegerField(default=1)
    size = models.PositiveBigIntegerField()
    content_type = models.CharField(max_length=100, default="application/pdf")
    sha256 = models.CharField(max_length=64)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_documents"
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.VALID)
    rejection_reason = models.TextField(blank=True)
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rejected_documents",
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_documents",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "documento"

    def __str__(self) -> str:
        return f"{self.original_name} ({self.get_status_display()})"


class PeriodEvent(models.Model):
    """Historial del período: solo inserción (sin endpoint de edición ni
    borrado). `actor` nulo = "Sistema" (generación automática, avisos)."""

    period = models.ForeignKey(Period, on_delete=models.CASCADE, related_name="events")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="period_events",
    )
    action = models.CharField(max_length=60)
    description = models.CharField(max_length=255)
    reason = models.TextField(blank=True)
    previous_value = models.CharField(max_length=255, blank=True)
    new_value = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name = "evento de período"

    def __str__(self) -> str:
        return f"{self.period.code} · {self.description}"
