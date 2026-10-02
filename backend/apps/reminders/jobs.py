"""Procesos programados (documento funcional, sección 7). Cada uno es
idempotente; el programador los ejecuta en cada ciclo y los que no tienen
nada que hacer simplemente no hacen nada."""

import logging

from django.utils import timezone

from apps.obligations.services import GenerationService

from . import services

logger = logging.getLogger("apps.reminders")


def run_all(now=None) -> dict:
    now = now or timezone.now()
    result = {
        "periods_created": len(GenerationService.generate(now)),
        "reminders_sent": services.run_due_reminders(now),
        "escalations_sent": services.run_escalations(now),
        "retries": services.retry_failed(now),
    }
    logger.info("Ciclo del programador completado", extra={"result": result})
    return result
