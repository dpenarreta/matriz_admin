"""Motor de estados (documento funcional, sección 6.1).

El estado de un período se calcula, no se guarda, con este orden:

1. Cerrado y cumplimiento <= vencimiento  -> Finalizado
2. Cerrado y cumplimiento >  vencimiento  -> Finalizado "fuera de plazo"
3. Abierto y ahora > vencimiento          -> Incumplido
4. Abierto y vence hoy (fecha local)      -> En progreso, marca "Vence hoy"
5. Abierto dentro del plazo               -> En progreso, con su etapa

Corrección respecto al mockup: "Vence hoy" es una **marca** (`is_due_today`)
y no reemplaza la etapa. Un período pendiente de validación sigue
pendiente de validación el día de su vencimiento, y el botón "Validar y
finalizar" sigue disponible.

Todas las fechas "del día" se evalúan en la zona horaria de la empresa,
nunca en la del navegador ni la del servidor.
"""

import math
from dataclasses import asdict, dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone

GROUP_OVERDUE = "incumplido"
GROUP_IN_PROGRESS = "en_progreso"
GROUP_DONE = "finalizado"

GROUP_LABELS = {
    GROUP_OVERDUE: "Incumplido",
    GROUP_IN_PROGRESS: "En progreso",
    GROUP_DONE: "Finalizado",
}

SECONDS_PER_DAY = 86400


@dataclass(frozen=True)
class PeriodStatus:
    group: str
    group_label: str
    label: str
    stage: str
    is_due_today: bool = False
    is_late: bool = False
    days_overdue: int = 0
    days_remaining: int | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def company_tz(period) -> ZoneInfo:
    return ZoneInfo(period.company.timezone)


def _ceil_days(delta_seconds: float) -> int:
    return max(1, math.ceil(delta_seconds / SECONDS_PER_DAY))


def compute_status(period, now: datetime | None = None) -> PeriodStatus:
    now = now or timezone.now()
    tz = company_tz(period)
    due = period.due_at
    stage_label = period.get_stage_display()

    if period.is_closed:
        completed = period.completed_at or period.validated_at or now
        late = completed > due
        return PeriodStatus(
            group=GROUP_DONE,
            group_label=GROUP_LABELS[GROUP_DONE],
            label="Finalizada fuera de plazo" if late else "Finalizado",
            stage=period.stage,
            is_late=late,
            days_overdue=_ceil_days((completed - due).total_seconds()) if late else 0,
        )

    if now > due:
        return PeriodStatus(
            group=GROUP_OVERDUE,
            group_label=GROUP_LABELS[GROUP_OVERDUE],
            label="Incumplido",
            stage=period.stage,
            days_overdue=_ceil_days((now - due).total_seconds()),
        )

    due_local = due.astimezone(tz).date()
    today_local = now.astimezone(tz).date()
    is_due_today = due_local == today_local
    return PeriodStatus(
        group=GROUP_IN_PROGRESS,
        group_label=GROUP_LABELS[GROUP_IN_PROGRESS],
        label="Vence hoy" if is_due_today else stage_label,
        stage=period.stage,
        is_due_today=is_due_today,
        days_remaining=(due_local - today_local).days,
    )


def status_q(group: str, now: datetime | None = None) -> Q:
    """Filtro ORM equivalente al grupo de estado, para no traer todo a
    memoria al filtrar la matriz."""
    now = now or timezone.now()
    if group == GROUP_DONE:
        return Q(is_closed=True)
    if group == GROUP_OVERDUE:
        return Q(is_closed=False, due_at__lt=now)
    if group == GROUP_IN_PROGRESS:
        return Q(is_closed=False, due_at__gte=now)
    raise ValueError(f"Grupo de estado desconocido: {group}")


def urgency_rank(now: datetime | None = None) -> Case:
    """Orden por urgencia de la matriz: incumplidos, en progreso, finalizados.
    Dentro de cada grupo se ordena por `due_at` (más atrasado / más próximo
    primero)."""
    now = now or timezone.now()
    return Case(
        When(status_q(GROUP_OVERDUE, now), then=Value(0)),
        When(status_q(GROUP_IN_PROGRESS, now), then=Value(1)),
        default=Value(2),
        output_field=IntegerField(),
    )
