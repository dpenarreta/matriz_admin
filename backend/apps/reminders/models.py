"""Configuración de recordatorios por empresa y registro de notificaciones
(documento funcional, secciones 3.2 y 6.4)."""

from datetime import time

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel
from apps.obligations.models import Period
from apps.organizations.models import Company

DEFAULT_OFFSETS = [15, 7, 3, 1, 0]


def default_offsets() -> list[int]:
    return list(DEFAULT_OFFSETS)


class ReminderConfig(BaseModel):
    """Una por empresa (en el mockup era una sola global: defecto 16)."""

    company = models.OneToOneField(
        Company, on_delete=models.CASCADE, related_name="reminder_config"
    )
    offsets = models.JSONField(default=default_offsets)
    send_time = models.TimeField(default=time(8, 0))
    copy_backup = models.BooleanField(default=True)
    escalation_enabled = models.BooleanField(default=True)
    escalation_days = models.PositiveSmallIntegerField(default=2)
    # 0 = se escala una sola vez; N = se repite cada N días mientras siga vencido.
    escalation_repeat_days = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "configuración de recordatorios"
        verbose_name_plural = "configuraciones de recordatorios"

    def clean(self):
        offsets = self.offsets or []
        if any(not isinstance(value, int) or value < 0 or value > 90 for value in offsets):
            raise ValidationError({"offsets": "Cada anticipación debe ser un entero entre 0 y 90."})
        if len(set(offsets)) != len(offsets):
            raise ValidationError({"offsets": "Las anticipaciones no pueden repetirse."})
        if not 1 <= self.escalation_days <= 30:
            raise ValidationError({"escalation_days": "Debe estar entre 1 y 30 días."})

    def normalized_offsets(self) -> list[int]:
        # El aviso del día del vencimiento siempre existe (sección 6.4).
        return sorted(set(self.offsets or []) | {0}, reverse=True)

    def __str__(self) -> str:
        return f"Recordatorios · {self.company}"


class Notification(BaseModel):
    class Kind(models.TextChoices):
        REMINDER = "recordatorio", "Recordatorio"
        DUE_DAY = "vencimiento", "Día del vencimiento"
        ESCALATION = "escalamiento", "Escalamiento"
        MANUAL = "manual", "Reenvío manual"

    class Status(models.TextChoices):
        SENT = "enviado", "Enviado"
        FAILED = "fallido", "Fallido"
        RETRIED = "reintentado", "Reintentado"

    period = models.ForeignKey(Period, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    offset_days = models.SmallIntegerField(null=True, blank=True)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    recipient_email = models.EmailField()
    scheduled_for = models.DateField(
        help_text="Fecha local de la empresa en que correspondía el aviso."
    )
    status = models.CharField(max_length=15, choices=Status.choices)
    attempts = models.PositiveSmallIntegerField(default=1)
    last_error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    retry_of = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="retries"
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_notifications",
    )
    # Clave de unicidad: un mismo aviso (período, tipo, anticipación,
    # destinatario, día) se registra una sola vez aunque el proceso corra dos
    # veces. Se usa un campo explícito porque SQL Server no admite varios
    # NULL en una restricción única compuesta.
    dedupe_key = models.CharField(max_length=200, unique=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "notificación"
        verbose_name_plural = "notificaciones"

    def __str__(self) -> str:
        return f"{self.get_kind_display()} · {self.period.code} · {self.recipient_email}"
