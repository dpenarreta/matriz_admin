"""Indicadores del Resumen y de Reportes (secciones 5.3 y 5.13).

Todo se calcula sobre el queryset ya filtrado por visibilidad del usuario,
así un Responsable solo ve indicadores de lo suyo.
"""

from collections import OrderedDict
from datetime import datetime

from django.utils import timezone

from .status import GROUP_DONE, GROUP_IN_PROGRESS, GROUP_OVERDUE, compute_status

UPCOMING_LIMIT = 6
RECENT_CLOSURES_LIMIT = 5
SOON_DAYS = 7


def _with_status(periods, now):
    return [(period, compute_status(period, now)) for period in periods]


def dashboard(queryset, now: datetime | None = None) -> dict:
    now = now or timezone.now()
    rows = _with_status(
        queryset.select_related("obligation", "company", "responsible").order_by("due_at"), now
    )
    counts = {GROUP_OVERDUE: 0, GROUP_IN_PROGRESS: 0, GROUP_DONE: 0}
    due_soon = on_time = late = attention = 0
    for _, status in rows:
        counts[status.group] += 1
        if status.group == GROUP_IN_PROGRESS and (status.days_remaining or 0) <= SOON_DAYS:
            due_soon += 1
        if status.group == GROUP_DONE:
            late += status.is_late
            on_time += not status.is_late
        if status.group == GROUP_OVERDUE or status.is_due_today:
            attention += 1
    upcoming = [period for period, status in rows if status.group != GROUP_DONE][:UPCOMING_LIMIT]
    recent = sorted(
        (period for period, status in rows if status.group == GROUP_DONE),
        key=lambda period: period.validated_at or period.updated_at,
        reverse=True,
    )[:RECENT_CLOSURES_LIMIT]
    return {
        "counts": {
            "overdue": counts[GROUP_OVERDUE],
            "in_progress": counts[GROUP_IN_PROGRESS],
            "due_soon": due_soon,
            "done": counts[GROUP_DONE],
            "done_on_time": on_time,
            "done_late": late,
            "attention": attention,
        },
        "upcoming": upcoming,
        "recent_closures": recent,
    }


def compliance_report(queryset, now: datetime | None = None) -> dict:
    now = now or timezone.now()
    rows = _with_status(
        queryset.select_related("obligation__area", "obligation__control_entity", "company"), now
    )
    by_area: dict[str, dict] = OrderedDict()
    by_entity: dict[str, dict] = OrderedDict()
    on_time = late = overdue = in_progress = 0
    for period, status in rows:
        bucket = {GROUP_DONE: "done", GROUP_IN_PROGRESS: "in_progress", GROUP_OVERDUE: "overdue"}[
            status.group
        ]
        for key, name, target in (
            (period.obligation.area.code, period.obligation.area.name, by_area),
            (
                period.obligation.control_entity.code,
                period.obligation.control_entity.name,
                by_entity,
            ),
        ):
            entry = target.setdefault(
                key,
                {"code": key, "name": name, "done": 0, "in_progress": 0, "overdue": 0, "total": 0},
            )
            entry[bucket] += 1
            entry["total"] += 1
        if status.group == GROUP_DONE:
            late += status.is_late
            on_time += not status.is_late
        elif status.group == GROUP_OVERDUE:
            overdue += 1
        else:
            in_progress += 1
    closed = on_time + late
    return {
        "kpis": {
            "on_time_pct": round(on_time * 100 / closed) if closed else 0,
            "late_pct": round(late * 100 / closed) if closed else 0,
            "closed": closed,
            "on_time": on_time,
            "late": late,
            "overdue": overdue,
            "in_progress": in_progress,
        },
        "by_area": sorted(by_area.values(), key=lambda item: item["name"]),
        "by_entity": sorted(by_entity.values(), key=lambda item: item["name"]),
    }
