"""Recordatorios, escalamiento y reintentos (sección 6.4)."""

from datetime import datetime, timedelta
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.utils import timezone

from apps.obligations.models import Period
from apps.obligations.tests.fixtures import client_for
from apps.reminders import services
from apps.reminders.models import Notification

pytestmark = pytest.mark.django_db
GYE = ZoneInfo("America/Guayaquil")


def at_local(days_from_today: int, hour: int) -> datetime:
    day = timezone.localdate() + timedelta(days=days_from_today)
    return datetime(day.year, day.month, day.day, hour, 0, tzinfo=GYE)


def test_reminder_sent_on_offset_day_after_send_time_and_only_once(make_period):
    period = make_period(days=7)
    now = at_local(0, 9)

    assert services.run_due_reminders(at_local(0, 7)) == 0  # antes de las 08:00
    sent = services.run_due_reminders(now)
    assert sent == 2  # responsable + suplente
    assert len(mail.outbox) == 2
    assert "Recordatorio de vencimiento" in mail.outbox[0].subject
    assert services.run_due_reminders(now) == 0  # idempotente
    assert Notification.objects.filter(period=period, offset_days=7).count() == 2


def test_no_reminder_on_days_not_configured(make_period):
    make_period(days=5)
    assert services.run_due_reminders(at_local(0, 9)) == 0


def test_closed_period_gets_no_reminders(make_period):
    period = make_period(days=7)
    Period.objects.filter(pk=period.pk).update(is_closed=True, reminders_suspended=True)
    assert services.run_due_reminders(at_local(0, 9)) == 0


def test_escalation_after_configured_days_goes_to_supervisor(make_period, people):
    period = make_period(days=-2)
    sent = services.run_escalations(at_local(0, 9))
    assert sent == 1
    assert mail.outbox[-1].to == [people["supervisor"].email]
    assert "Escalamiento" in mail.outbox[-1].subject
    assert period.events.filter(action="period.escalated").exists()
    assert services.run_escalations(at_local(0, 9)) == 0


def test_no_escalation_before_threshold(make_period):
    make_period(days=-1)
    assert services.run_escalations(at_local(0, 9)) == 0


def test_failed_send_is_recorded_and_retry_creates_new_row(make_period):
    period = make_period(days=7)
    with mock.patch(
        "apps.reminders.services.EmailMultiAlternatives.send", side_effect=OSError("smtp caído")
    ):
        services.run_due_reminders(at_local(0, 9))
    failed = Notification.objects.filter(period=period, status=Notification.Status.FAILED)
    assert failed.count() == 2

    retried = services.retry_failed()
    assert retried == 2
    assert Notification.objects.filter(status=Notification.Status.RETRIED).count() == 2
    assert (
        Notification.objects.filter(status=Notification.Status.SENT, retry_of__isnull=False).count()
        == 2
    )


def test_manual_send_and_preview(people, make_period):
    period = make_period(days=10)
    client = client_for(people["responsible"])
    response = client.post(f"/api/v1/periods/{period.id}/reminders/send/")
    assert response.status_code == 201
    preview = client.get(f"/api/v1/periods/{period.id}/reminders/preview/").data
    assert period.code in preview["html"]
    assert preview["to"] == people["responsible"].email


def test_schedule_lists_configured_offsets(people, make_period):
    period = make_period(days=10)
    data = client_for(people["responsible"]).get(f"/api/v1/periods/{period.id}/reminders/").data
    assert [item["offset_days"] for item in data["schedule"]] == [15, 7, 3, 1, 0]
    assert data["schedule"][0]["state"] == "no_enviado"
    assert data["schedule"][1]["state"] == "programado"


def test_reminder_config_validation_and_permissions(company, people):
    url = f"/api/v1/companies/{company.id}/reminder-config/"
    assert (
        client_for(people["supervisor"]).put(url, {"offsets": [10]}, format="json").status_code
        == 403
    )
    admin = client_for(people["admin"])
    assert admin.put(url, {"offsets": [5, 5]}, format="json").status_code == 400
    response = admin.put(url, {"offsets": [10, 2], "escalation_days": 3}, format="json")
    assert response.status_code == 200
    assert response.data["offsets"] == [10, 2, 0]
