"""Envío de recordatorios, escalamiento y reintentos (sección 6.4).

Todas las funciones de proceso (`run_*`) son idempotentes: se pueden
ejecutar varias veces el mismo día sin duplicar avisos, gracias a
`Notification.dedupe_key`. Las fechas "del día" son las de la zona horaria
de cada empresa.
"""

import logging
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string
from django.utils import timezone

from apps.obligations.models import Period
from apps.obligations.services import record_event
from apps.obligations.status import compute_status
from apps.organizations.models import Company
from apps.organizations.serializers import full_name

from .models import Notification, ReminderConfig

logger = logging.getLogger("apps.reminders")

Kind = Notification.Kind

MONTH_NAMES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def get_config(company: Company) -> ReminderConfig:
    config, _ = ReminderConfig.objects.get_or_create(company=company)
    return config


def _local(dt: datetime, company: Company) -> datetime:
    return dt.astimezone(ZoneInfo(company.timezone))


def reminder_recipients(period: Period, config: ReminderConfig) -> list:
    people = [period.responsible]
    if config.copy_backup and period.backup:
        people.append(period.backup)
    return _unique_with_email(people)


def escalation_recipients(period: Period) -> list:
    return _unique_with_email([period.supervisor or period.approver])


def _unique_with_email(people) -> list:
    seen, result = set(), []
    for person in people:
        if person is None or not person.email or person.email.lower() in seen:
            continue
        seen.add(person.email.lower())
        result.append(person)
    return result


def render_message(period: Period, kind: str, recipient, now: datetime | None = None) -> dict:
    status = compute_status(period, now)
    due_local = _local(period.due_at, period.company)
    subjects = {
        Kind.ESCALATION: f"Escalamiento: obligación vencida — {period.obligation.name} ({period.label})",
        Kind.DUE_DAY: f"Hoy vence — {period.obligation.name} ({period.label})",
    }
    subject = subjects.get(
        kind, f"Recordatorio de vencimiento — {period.obligation.name} ({period.label})"
    )
    context = {
        "system_name": settings.SYSTEM_NAME,
        "recipient_name": full_name(recipient),
        "is_escalation": kind == Kind.ESCALATION,
        "period": period,
        "obligation": period.obligation,
        "company": period.company,
        "responsible_name": full_name(period.responsible),
        "due_text": f"{due_local.day} de {MONTH_NAMES[due_local.month - 1]} de {due_local.year} · {due_local:%H:%M}",
        "status": status,
        "detail_url": f"{settings.FRONTEND_URL.rstrip('/')}/matriz?periodo={period.id}",
    }
    return {
        "subject": subject,
        "to": recipient.email,
        "text": render_to_string("emails/reminder.txt", context),
        "html": render_to_string("emails/reminder.html", context),
    }


def _send(period: Period, kind: str, recipient) -> tuple[bool, str]:
    message = render_message(period, kind, recipient)
    email = EmailMultiAlternatives(
        subject=message["subject"],
        body=message["text"],
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[message["to"]],
    )
    email.attach_alternative(message["html"], "text/html")
    try:
        email.send(fail_silently=False)
        return True, ""
    except Exception as exc:  # noqa: BLE001 — cualquier fallo del proveedor queda registrado
        logger.warning("Fallo al enviar notificación %s a %s: %s", kind, recipient.email, exc)
        return False, str(exc)[:1000]


def deliver(
    *,
    period: Period,
    kind: str,
    recipient,
    scheduled_for,
    dedupe_key: str,
    offset_days: int | None = None,
    triggered_by=None,
    retry_of: Notification | None = None,
    attempts: int = 1,
) -> Notification | None:
    """Registra la notificación (reservando su clave) y envía el correo. Si la
    clave ya existe, otro proceso ya se encargó: no se reenvía."""
    try:
        with transaction.atomic():
            notification = Notification.objects.create(
                period=period,
                kind=kind,
                offset_days=offset_days,
                recipient=recipient,
                recipient_email=recipient.email,
                scheduled_for=scheduled_for,
                status=Notification.Status.FAILED,
                attempts=attempts,
                retry_of=retry_of,
                triggered_by=triggered_by,
                dedupe_key=dedupe_key,
            )
    except IntegrityError:
        return None
    ok, error = _send(period, kind, recipient)
    notification.status = Notification.Status.SENT if ok else Notification.Status.FAILED
    notification.sent_at = timezone.now() if ok else None
    notification.last_error = error
    notification.save(update_fields=["status", "sent_at", "last_error", "updated_at"])
    return notification


def _open_periods(company: Company):
    return Period.objects.filter(
        company=company, is_closed=False, reminders_suspended=False
    ).select_related("obligation", "company", "responsible", "backup", "supervisor", "approver")


def run_due_reminders(now: datetime | None = None) -> int:
    now = now or timezone.now()
    sent = 0
    for company in Company.objects.filter(is_active=True):
        config = get_config(company)
        local_now = _local(now, company)
        if local_now.time() < config.send_time:
            continue
        today = local_now.date()
        offsets = config.normalized_offsets()
        for period in _open_periods(company).filter(
            due_at__gte=now - timedelta(days=1), due_at__lte=now + timedelta(days=max(offsets) + 1)
        ):
            due_local = _local(period.due_at, company).date()
            offset = (due_local - today).days
            if offset not in offsets:
                continue
            kind = Kind.DUE_DAY if offset == 0 else Kind.REMINDER
            for person in reminder_recipients(period, config):
                key = f"auto:{period.id}:{kind}:{offset}:{person.email.lower()}:{due_local}"
                if deliver(
                    period=period,
                    kind=kind,
                    recipient=person,
                    scheduled_for=today,
                    dedupe_key=key,
                    offset_days=offset,
                ):
                    sent += 1
    return sent


def run_escalations(now: datetime | None = None) -> int:
    now = now or timezone.now()
    sent = 0
    for company in Company.objects.filter(is_active=True):
        config = get_config(company)
        if not config.escalation_enabled:
            continue
        local_now = _local(now, company)
        if local_now.time() < config.send_time:
            continue
        today = local_now.date()
        for period in _open_periods(company).filter(due_at__lt=now):
            due_local = _local(period.due_at, company).date()
            days_late = (today - due_local).days
            if days_late < config.escalation_days:
                continue
            if config.escalation_repeat_days:
                if (days_late - config.escalation_days) % config.escalation_repeat_days:
                    continue
                suffix = f"{due_local}:{today}"
            else:
                suffix = f"{due_local}"
            for person in escalation_recipients(period):
                key = f"esc:{period.id}:{person.email.lower()}:{suffix}"
                notification = deliver(
                    period=period,
                    kind=Kind.ESCALATION,
                    recipient=person,
                    scheduled_for=today,
                    dedupe_key=key,
                    offset_days=-days_late,
                )
                if notification:
                    sent += 1
                    record_event(
                        period,
                        actor=None,
                        action="period.escalated",
                        description=f"Escalamiento enviado a {full_name(person)}",
                        reason=f"{days_late} día(s) de atraso",
                    )
    return sent


def retry(notification: Notification, *, triggered_by=None) -> Notification | None:
    """Reintenta un aviso fallido: crea una fila nueva y marca la original
    como "Reintentado" (no se duplica el aviso original)."""
    if notification.status != Notification.Status.FAILED:
        return None
    recipient = notification.recipient
    if recipient is None:
        return None
    new = deliver(
        period=notification.period,
        kind=notification.kind,
        recipient=recipient,
        scheduled_for=notification.scheduled_for,
        dedupe_key=f"retry:{notification.id}:{notification.attempts + 1}",
        offset_days=notification.offset_days,
        triggered_by=triggered_by,
        retry_of=notification,
        attempts=notification.attempts + 1,
    )
    if new is not None:
        notification.status = Notification.Status.RETRIED
        notification.save(update_fields=["status", "updated_at"])
    return new


def retry_failed(now: datetime | None = None) -> int:
    now = now or timezone.now()
    count = 0
    candidates = Notification.objects.filter(
        status=Notification.Status.FAILED,
        attempts__lt=settings.NOTIFICATION_MAX_ATTEMPTS,
        created_at__gte=now - timedelta(days=7),
        period__is_closed=False,
    ).select_related("period", "recipient")
    for notification in candidates:
        if retry(notification):
            count += 1
    return count


def send_manual(period: Period, *, actor) -> list[Notification]:
    config = get_config(period.company)
    today = _local(timezone.now(), period.company).date()
    notifications = []
    for person in reminder_recipients(period, config):
        notification = deliver(
            period=period,
            kind=Kind.MANUAL,
            recipient=person,
            scheduled_for=today,
            dedupe_key=f"manual:{uuid.uuid4().hex}",
            triggered_by=actor,
        )
        if notification:
            notifications.append(notification)
    record_event(
        period,
        actor=actor,
        action="period.reminder_sent",
        description="Recordatorio reenviado manualmente",
    )
    return notifications


def schedule(period: Period, now: datetime | None = None) -> list[dict]:
    """Avisos del período según la configuración actual, con su estado
    real: Enviado / Fallido si existe la notificación, Programado si es
    futuro, No enviado si la fecha pasó sin registro."""
    now = now or timezone.now()
    company = period.company
    config = get_config(company)
    due_local = _local(period.due_at, company)
    existing = {
        (n.kind, n.offset_days): n
        for n in period.notifications.filter(kind__in=[Kind.REMINDER, Kind.DUE_DAY]).order_by(
            "created_at"
        )
    }
    items = []
    for offset in config.normalized_offsets():
        kind = Kind.DUE_DAY if offset == 0 else Kind.REMINDER
        send_at = datetime.combine(
            due_local.date() - timedelta(days=offset),
            config.send_time,
            tzinfo=ZoneInfo(company.timezone),
        )
        notification = existing.get((kind, offset))
        if period.reminders_suspended and notification is None:
            state = "suspendido"
        elif notification is not None:
            state = notification.status
        elif send_at > now:
            state = "programado"
        else:
            state = "no_enviado"
        items.append({"offset_days": offset, "kind": kind, "send_at": send_at, "state": state})
    return items
