"""Programador de tareas: genera períodos, envía recordatorios, escala atrasos
y reintenta avisos fallidos, aunque nadie tenga la aplicación abierta.

    python manage.py run_scheduler           # bucle (servicio `worker`)
    python manage.py run_scheduler --once    # un ciclo (para cron / tareas del SO)
"""

import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.reminders.jobs import run_all


class Command(BaseCommand):
    help = "Ejecuta los procesos programados de la matriz (uno o en bucle)."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Ejecuta un solo ciclo y termina.")
        parser.add_argument(
            "--interval",
            type=int,
            default=settings.SCHEDULER_INTERVAL_SECONDS,
            help="Segundos entre ciclos (por defecto SCHEDULER_INTERVAL_SECONDS).",
        )

    def handle(self, *args, **options):
        while True:
            close_old_connections()
            try:
                result = run_all()
                self.stdout.write(f"Ciclo completado: {result}")
            except Exception as exc:  # noqa: BLE001 — un ciclo fallido no detiene el servicio
                self.stderr.write(f"Ciclo con error: {exc}")
                if options["once"]:
                    raise
            if options["once"]:
                return
            time.sleep(max(30, options["interval"]))
