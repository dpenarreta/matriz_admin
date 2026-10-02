from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import record_audit_event
from apps.core.pagination import DefaultPagination
from apps.core.request_meta import get_request_context
from apps.obligations.policies import access_for_period, require_period_capability
from apps.obligations.views import get_period
from apps.organizations.access import Cap, require_access, require_capability
from apps.organizations.views import get_company

from . import services
from .models import Notification
from .serializers import NotificationSerializer, ReminderConfigSerializer


class ReminderConfigView(APIView):
    def get(self, request, company_id):
        company = get_company(company_id)
        require_access(request, company)
        return Response(ReminderConfigSerializer(services.get_config(company)).data)

    def put(self, request, company_id):
        company = get_company(company_id)
        require_capability(
            request, company, Cap.CONFIGURE, "Solo un Administrador puede editar los recordatorios."
        )
        config = services.get_config(company)
        previous = dict(ReminderConfigSerializer(config).data)
        serializer = ReminderConfigSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        record_audit_event(
            actor=request.user,
            action="reminder_config.updated",
            module="matriz",
            target=company,
            previous_values=previous,
            new_values=dict(serializer.data),
            context=get_request_context(request),
        )
        return Response(serializer.data)


class PeriodRemindersView(APIView):
    def get(self, request, period_id):
        period = get_period(period_id)
        access_for_period(request, period)
        notifications = period.notifications.select_related("period__obligation").order_by(
            "-created_at"
        )
        return Response(
            {
                "suspended": period.reminders_suspended,
                "schedule": services.schedule(period),
                "notifications": NotificationSerializer(notifications, many=True).data,
            }
        )


class PeriodReminderSendView(APIView):
    def post(self, request, period_id):
        period = get_period(period_id)
        require_period_capability(request, period, Cap.REMIND)
        if period.is_closed or period.reminders_suspended:
            raise ValidationError(
                {"detail": "Los recordatorios de este período están suspendidos (cierre validado)."}
            )
        notifications = services.send_manual(period, actor=request.user)
        return Response(
            NotificationSerializer(notifications, many=True).data, status=status.HTTP_201_CREATED
        )


class PeriodReminderPreviewView(APIView):
    def get(self, request, period_id):
        period = get_period(period_id)
        access_for_period(request, period)
        kind = request.query_params.get("kind", Notification.Kind.REMINDER)
        if kind not in Notification.Kind.values:
            raise ValidationError({"kind": "Tipo de aviso desconocido."})
        recipient = period.supervisor if kind == Notification.Kind.ESCALATION else None
        return Response(services.render_message(period, kind, recipient or period.responsible))


class CompanyNotificationsView(APIView):
    def get(self, request, company_id):
        company = get_company(company_id)
        require_capability(request, company, Cap.VIEW_AUDIT)
        queryset = Notification.objects.filter(period__company=company).select_related(
            "period__obligation"
        )
        if request.query_params.get("status"):
            queryset = queryset.filter(status=request.query_params["status"])
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset.order_by("-created_at"), request, view=self)
        return paginator.get_paginated_response(NotificationSerializer(page, many=True).data)


class NotificationRetryView(APIView):
    def post(self, request, notification_id):
        notification = get_object_or_404(
            Notification.objects.select_related("period__company", "recipient"), pk=notification_id
        )
        require_period_capability(request, notification.period, Cap.REMIND)
        new = services.retry(notification, triggered_by=request.user)
        if new is None:
            raise ValidationError({"detail": "Solo se reintenta un aviso fallido."})
        return Response(NotificationSerializer(new).data, status=status.HTTP_201_CREATED)
