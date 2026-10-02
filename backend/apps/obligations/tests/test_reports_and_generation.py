"""Generación de períodos (6.5), Resumen, Reportes y exportaciones."""

from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.obligations.models import Obligation, Period
from apps.obligations.scheduling import add_months, next_due_date, period_label
from apps.obligations.services import GenerationService
from apps.obligations.tests.fixtures import client_for

pytestmark = pytest.mark.django_db


def test_labels_by_periodicity():
    due = date(2026, 10, 28)
    assert period_label("mensual", due) == "Octubre 2026"
    assert period_label("trimestral", due) == "T4 2026"
    assert period_label("semestral", due) == "S2 2026"
    assert period_label("anual", due) == "Período 2026"
    assert period_label("unica", due) == "Período único"


def test_month_arithmetic_clamps_to_month_length():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)


def test_next_due_uses_template_day(obligation):
    assert next_due_date(obligation, date(2026, 1, 28)) == date(2026, 2, 28)


def test_generation_creates_next_period_and_is_idempotent(obligation, make_period, people):
    current = make_period(days=10, label="Actual")
    created = GenerationService.generate()
    assert len(created) >= 1
    nxt = created[0]
    assert nxt.responsible == current.responsible
    assert nxt.due_at > current.due_at
    assert GenerationService.generate() == []


def test_generation_skips_once_and_inactive(obligation, make_period):
    obligation.periodicity = Obligation.Periodicity.ONCE
    obligation.save()
    make_period(days=3, label="Única")
    assert GenerationService.generate() == []


def test_dashboard_counts(company, people, make_period):
    make_period(days=-2, label="Vencido")
    make_period(days=3, label="Pronto")
    make_period(days=20, label="Lejos")
    closed = make_period(days=-10, label="Cerrado")
    Period.objects.filter(pk=closed.pk).update(
        is_closed=True, completed_at=closed.due_at - timedelta(days=1)
    )

    data = client_for(people["admin"]).get(f"/api/v1/companies/{company.id}/dashboard/").data

    assert data["counts"]["overdue"] == 1
    assert data["counts"]["in_progress"] == 2
    assert data["counts"]["due_soon"] == 1
    assert data["counts"]["done_on_time"] == 1
    assert data["upcoming"][0]["label"] == "Vencido"


def test_report_groups_by_area_and_entity(company, people, make_period):
    make_period(days=-2, label="Vencido")
    make_period(days=5, label="Abierto")
    report = client_for(people["supervisor"]).get(f"/api/v1/companies/{company.id}/reports/").data
    assert report["by_area"][0]["overdue"] == 1
    assert report["by_area"][0]["in_progress"] == 1
    assert report["by_entity"][0]["total"] == 2


@pytest.mark.parametrize(
    "fmt,content_type", [("xlsx", "spreadsheetml"), ("pdf", "application/pdf")]
)
def test_exports_are_real_files(company, people, make_period, fmt, content_type):
    make_period(days=5)
    response = client_for(people["supervisor"]).get(
        f"/api/v1/companies/{company.id}/periods/?export={fmt}"
    )
    assert response.status_code == 200
    assert content_type in response["Content-Type"]
    assert len(response.content) > 500


def test_matrix_filters_and_urgency_sort(company, people, make_period):
    make_period(days=20, label="Lejos")
    make_period(days=-1, label="Vencido")
    make_period(days=2, label="Cerca")
    client = client_for(people["admin"])

    rows = client.get(f"/api/v1/companies/{company.id}/periods/").data["results"]
    assert [row["label"] for row in rows] == ["Vencido", "Cerca", "Lejos"]

    overdue = client.get(f"/api/v1/companies/{company.id}/periods/?status=incumplido").data
    assert overdue["count"] == 1
    search = client.get(f"/api/v1/companies/{company.id}/periods/?q=iva").data
    assert search["count"] == 3


def test_calendar_returns_month_periods(company, people, make_period):
    period = make_period(days=1)
    local = timezone.localtime(period.due_at)
    data = (
        client_for(people["admin"])
        .get(f"/api/v1/companies/{company.id}/calendar/?year={local.year}&month={local.month}")
        .data
    )
    assert period.code in [row["code"] for row in data]
