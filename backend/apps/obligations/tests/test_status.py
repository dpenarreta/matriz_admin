"""Motor de estados (documento funcional, sección 6.1)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from apps.obligations.models import Period
from apps.obligations.status import compute_status

pytestmark = pytest.mark.django_db
GYE = ZoneInfo("America/Guayaquil")


def test_open_period_before_due_is_in_progress_with_its_stage(make_period):
    period = make_period(days=5)
    status = compute_status(period)
    assert status.group == "en_progreso"
    assert status.label == "Sin iniciar"
    assert status.days_remaining == 5
    assert not status.is_due_today


def test_period_past_due_without_closure_is_overdue(make_period):
    period = make_period(days=-3)
    status = compute_status(period)
    assert status.group == "incumplido"
    assert status.days_overdue >= 3


def test_due_today_is_a_flag_and_keeps_the_pending_validation_stage(make_period):
    """Corrección del mockup: "Vence hoy" no reemplaza la etapa."""
    period = make_period(days=0)
    period.stage = Period.Stage.PENDING_VALIDATION
    morning = period.due_at.astimezone(GYE).replace(hour=8, minute=0)
    status = compute_status(period, now=morning)
    assert status.group == "en_progreso"
    assert status.is_due_today
    assert status.label == "Vence hoy"
    assert status.stage == Period.Stage.PENDING_VALIDATION


def test_closed_on_time_and_closed_late(make_period):
    on_time = make_period(days=-10, label="A")
    on_time.is_closed, on_time.completed_at = True, on_time.due_at - timedelta(days=2)
    late = make_period(days=-10, label="B")
    late.is_closed, late.completed_at = True, late.due_at + timedelta(days=4)

    assert compute_status(on_time).label == "Finalizado"
    assert not compute_status(on_time).is_late
    late_status = compute_status(late)
    assert late_status.group == "finalizado"
    assert late_status.label == "Finalizada fuera de plazo"
    assert late_status.days_overdue == 4


def test_overdue_flips_right_after_the_due_hour_in_company_timezone(make_period):
    period = make_period(days=0)
    due_local = period.due_at.astimezone(GYE)
    just_before = due_local - timedelta(minutes=1)
    just_after = due_local + timedelta(minutes=1)
    assert compute_status(period, now=just_before).group == "en_progreso"
    assert compute_status(period, now=just_after).group == "incumplido"


def test_due_time_defaults_to_17h_local(make_period):
    period = make_period(days=3)
    assert period.due_at.astimezone(GYE).hour == 17
    assert isinstance(period.due_at, datetime)
