"""Cálculo de fechas, etiquetas y códigos de los períodos (sección 6.5).

Convención: el período se nombra por el mes (o trimestre, semestre, año)
de su **vencimiento**. Ej.: un IVA mensual que vence el 28 de octubre de
2026 es el período "Octubre 2026".
"""

import calendar
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction

from .models import CodeSequence, Obligation

MONTHS = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]

STEP_MONTHS = {
    Obligation.Periodicity.MONTHLY: 1,
    Obligation.Periodicity.QUARTERLY: 3,
    Obligation.Periodicity.SEMIANNUAL: 6,
    Obligation.Periodicity.ANNUAL: 12,
}

DEFAULT_START_OFFSET_DAYS = 30
DEFAULT_PREPARATION_OFFSET_DAYS = 5


def period_label(periodicity: str, due: date) -> str:
    if periodicity == Obligation.Periodicity.MONTHLY:
        return f"{MONTHS[due.month - 1]} {due.year}"
    if periodicity == Obligation.Periodicity.QUARTERLY:
        return f"T{(due.month - 1) // 3 + 1} {due.year}"
    if periodicity == Obligation.Periodicity.SEMIANNUAL:
        return f"S{1 if due.month <= 6 else 2} {due.year}"
    if periodicity == Obligation.Periodicity.ANNUAL:
        return f"Período {due.year}"
    return "Período único"


def clamp_day(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def add_months(base: date, months: int, day: int | None = None) -> date:
    index = base.month - 1 + months
    year, month = base.year + index // 12, index % 12 + 1
    return clamp_day(year, month, day or base.day)


def next_due_date(obligation: Obligation, previous_due: date) -> date | None:
    step = STEP_MONTHS.get(obligation.periodicity)
    if step is None:
        return None
    return add_months(previous_due, step, obligation.due_day or previous_due.day)


def first_due_date(obligation: Obligation, today: date) -> date:
    """Primer vencimiento >= hoy según la regla de la plantilla. Si la
    plantilla no tiene regla, vence en 30 días."""
    day = obligation.due_day
    if obligation.periodicity == Obligation.Periodicity.ANNUAL and obligation.due_month and day:
        candidate = clamp_day(today.year, obligation.due_month, day)
        return (
            candidate
            if candidate >= today
            else clamp_day(today.year + 1, obligation.due_month, day)
        )
    if obligation.periodicity in STEP_MONTHS and day:
        candidate = clamp_day(today.year, today.month, day)
        return candidate if candidate >= today else add_months(candidate, 1, day)
    return today + timedelta(days=DEFAULT_START_OFFSET_DAYS)


def local_due_datetime(company, due: date, due_time) -> datetime:
    return datetime.combine(due, due_time, tzinfo=ZoneInfo(company.timezone))


def default_dates(due: date) -> tuple[date, date]:
    return (
        due - timedelta(days=DEFAULT_START_OFFSET_DAYS),
        due - timedelta(days=DEFAULT_PREPARATION_OFFSET_DAYS),
    )


def next_code() -> str:
    """`OBL-0001`, `OBL-0002`, … Debe llamarse dentro de una transacción."""
    with transaction.atomic():
        sequence, _ = CodeSequence.objects.select_for_update().get_or_create(name="period")
        sequence.last_value += 1
        sequence.save(update_fields=["last_value"])
    return f"{settings.PERIOD_CODE_PREFIX}-{sequence.last_value:04d}"
