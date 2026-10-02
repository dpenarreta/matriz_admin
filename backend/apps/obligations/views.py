"""Endpoints de la matriz (documento funcional, sección 7).

Cada vista: (1) resuelve la empresa o el período, (2) exige membresía y
capacidad (`apps.organizations.access` / `apps.obligations.policies`),
(3) delega en un `*Service`. Ninguna regla de negocio vive aquí.
"""

from datetime import date

from django.db.models import Count, Q
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import record_audit_event
from apps.core.pagination import DefaultPagination
from apps.core.request_meta import get_request_context
from apps.organizations.access import Cap, deny, require_access, require_capability
from apps.organizations.models import Area, ControlEntity
from apps.organizations.serializers import AreaSerializer, BranchSerializer, ControlEntitySerializer
from apps.organizations.views import get_company

from . import exports, reports
from .models import Document, Obligation, Period, PeriodEvent
from .policies import access_for_period, period_actions, require_period_capability, visible_periods
from .serializers import (
    AuditEventSerializer,
    DocumentSerializer,
    DueDateChangeSerializer,
    ObligationCreateSerializer,
    ObligationSerializer,
    ObligationWriteSerializer,
    PeriodDetailSerializer,
    PeriodEventSerializer,
    PeriodListSerializer,
    PeriodUpdateSerializer,
    ReasonSerializer,
    UploadSerializer,
    catalog_choices,
)
from .services import DocumentService, ObligationService, PeriodService
from .status import GROUP_LABELS, status_q, urgency_rank

PERIOD_RELATED = (
    "obligation",
    "obligation__area",
    "obligation__control_entity",
    "company",
    "responsible",
    "backup",
    "supervisor",
    "approver",
    "submitted_by",
    "validated_by",
    "branch",
)

SORT_FIELDS = {
    "due": "due_at",
    "name": "obligation__name",
    "area": "obligation__area__name",
    "entity": "obligation__control_entity__name",
    "responsible": "responsible__first_name",
    "code": "code",
    "priority": "priority",
}


def get_period(period_id) -> Period:
    return get_object_or_404(Period.objects.select_related(*PERIOD_RELATED), pk=period_id)


def period_detail_response(request, period: Period, http_status=status.HTTP_200_OK) -> Response:
    period = get_period(period.pk)
    access = access_for_period(request, period)
    serializer = PeriodDetailSerializer(
        period,
        context={"now": timezone.now(), "actions": period_actions(access, request.user, period)},
    )
    return Response(serializer.data, status=http_status)


def _parse_date(value, field):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError({field: "Fecha inválida, use AAAA-MM-DD."}) from exc


def filtered_periods(request, access):
    """Filtros de la matriz (sección 5.4), aplicados en la base de datos."""
    params = request.query_params
    now = timezone.now()
    queryset = visible_periods(access, request.user).select_related(*PERIOD_RELATED)
    query = (params.get("q") or "").strip()
    if query:
        queryset = queryset.filter(
            Q(obligation__name__icontains=query)
            | Q(code__icontains=query)
            | Q(label__icontains=query)
            | Q(responsible__first_name__icontains=query)
            | Q(responsible__last_name__icontains=query)
            | Q(responsible__username__icontains=query)
            | Q(obligation__control_entity__name__icontains=query)
            | Q(obligation__area__name__icontains=query)
        )
    for param, lookup in (
        ("area", "obligation__area_id"),
        ("entity", "obligation__control_entity_id"),
        ("responsible", "responsible_id"),
        ("obligation", "obligation_id"),
        ("priority", "priority"),
        ("stage", "stage"),
    ):
        if params.get(param):
            queryset = queryset.filter(**{lookup: params[param]})
    group = params.get("status")
    if group:
        if group not in GROUP_LABELS:
            raise ValidationError({"status": "Estado desconocido."})
        queryset = queryset.filter(status_q(group, now))
    if params.get("due_today") == "true":
        today = timezone.localtime(now).date()
        queryset = queryset.filter(is_closed=False, due_at__date=today)
    due_from, due_to = _parse_date(params.get("due_from"), "due_from"), _parse_date(
        params.get("due_to"), "due_to"
    )
    if due_from:
        queryset = queryset.filter(due_at__date__gte=due_from)
    if due_to:
        queryset = queryset.filter(due_at__date__lte=due_to)

    sort = params.get("sort", "urgency")
    descending = sort.startswith("-")
    key = sort.lstrip("-")
    if key == "urgency":
        queryset = queryset.annotate(_rank=urgency_rank(now)).order_by(
            "-_rank" if descending else "_rank", "due_at", "id"
        )
    elif key in SORT_FIELDS:
        field = SORT_FIELDS[key]
        queryset = queryset.order_by(f"-{field}" if descending else field, "due_at", "id")
    else:
        raise ValidationError({"sort": "Orden desconocido."})
    return queryset.annotate(
        valid_documents=Count("documents", filter=Q(documents__status=Document.Status.VALID))
    )


class CatalogsView(APIView):
    def get(self, request, company_id):
        company = get_company(company_id)
        require_access(request, company)
        return Response(
            {
                "areas": AreaSerializer(Area.objects.all(), many=True).data,
                "control_entities": ControlEntitySerializer(
                    ControlEntity.objects.all(), many=True
                ).data,
                "branches": BranchSerializer(
                    company.branches.filter(is_active=True), many=True
                ).data,
                **catalog_choices(),
            }
        )


class DashboardView(APIView):
    def get(self, request, company_id):
        company = get_company(company_id)
        access = require_access(request, company)
        now = timezone.now()
        data = reports.dashboard(visible_periods(access, request.user), now)
        context = {"now": now}
        return Response(
            {
                "counts": data["counts"],
                "upcoming": PeriodListSerializer(data["upcoming"], many=True, context=context).data,
                "recent_closures": PeriodListSerializer(
                    data["recent_closures"], many=True, context=context
                ).data,
            }
        )


class PeriodListView(APIView):
    def get(self, request, company_id):
        company = get_company(company_id)
        access = require_access(request, company)
        queryset = filtered_periods(request, access)
        export_format = request.query_params.get("export")
        if export_format:
            if not access.has(Cap.EXPORT):
                deny(request, "Su rol no permite exportar la matriz.", capability=Cap.EXPORT)
            return export_response(
                request,
                company,
                export_format,
                title="Matriz de obligaciones",
                headers=exports.MATRIX_HEADERS,
                rows=list(exports.matrix_rows(queryset)),
            )
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        data = PeriodListSerializer(page, many=True, context={"now": timezone.now()}).data
        return paginator.get_paginated_response(data)


def export_response(request, company, export_format, *, title, headers, rows) -> HttpResponse:
    if export_format not in {"xlsx", "pdf"}:
        raise ValidationError({"export": "Formato no soportado: use xlsx o pdf."})
    builder = exports.to_xlsx if export_format == "xlsx" else exports.to_pdf
    content = builder(company=company, user=request.user, title=title, headers=headers, rows=rows)
    content_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if export_format == "xlsx"
        else "application/pdf"
    )
    stamp = timezone.localtime().strftime("%Y%m%d-%H%M")
    filename = f"{title.lower().replace(' ', '-')}-{company.code}-{stamp}.{export_format}"
    record_audit_event(
        actor=request.user,
        action="report.exported",
        module="matriz",
        target=company,
        new_values={"title": title, "format": export_format, "rows": len(rows)},
        context=get_request_context(request),
    )
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


class ObligationCreateView(APIView):
    def post(self, request, company_id):
        company = get_company(company_id)
        access = require_capability(
            request, company, Cap.CREATE, "Su rol no tiene permiso para crear obligaciones."
        )
        serializer = ObligationCreateSerializer(data=request.data, context={"company": company})
        serializer.is_valid(raise_exception=True)
        obligation_data, period_data = serializer.split()
        if not access.can_create_in_area(obligation_data["area"].id):
            deny(
                request,
                "Solo puede crear obligaciones de sus áreas asignadas.",
                capability=Cap.CREATE,
            )
        _, period = ObligationService.create(
            actor=request.user,
            company=company,
            obligation_data=obligation_data,
            period_data=period_data,
            context=get_request_context(request),
        )
        return period_detail_response(request, period, status.HTTP_201_CREATED)


class ObligationDetailView(APIView):
    def _get(self, request, obligation_id):
        obligation = get_object_or_404(
            Obligation.objects.select_related("company", "area", "control_entity"), pk=obligation_id
        )
        return obligation, require_access(request, obligation.company)

    def get(self, request, obligation_id):
        obligation, _ = self._get(request, obligation_id)
        return Response(ObligationSerializer(obligation).data)

    def patch(self, request, obligation_id):
        obligation, access = self._get(request, obligation_id)
        if not access.has(Cap.EDIT):
            deny(request, "Su rol no permite editar obligaciones.", capability=Cap.EDIT)
        if access.is_scoped(Cap.EDIT):
            owns_one = obligation.periods.filter(
                Q(responsible=request.user) | Q(backup=request.user)
            ).exists()
            if not owns_one or not access.can_create_in_area(obligation.area_id):
                deny(
                    request,
                    "Solo puede editar obligaciones que tiene asignadas.",
                    capability=Cap.EDIT,
                )
        serializer = ObligationWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obligation = ObligationService.update(
            actor=request.user,
            obligation=obligation,
            context=get_request_context(request),
            **serializer.validated_data,
        )
        return Response(ObligationSerializer(obligation).data)


class PeriodDetailView(APIView):
    def get(self, request, period_id):
        return period_detail_response(request, get_period(period_id))

    def patch(self, request, period_id):
        period = get_period(period_id)
        require_period_capability(request, period, Cap.EDIT)
        serializer = PeriodUpdateSerializer(
            data=request.data, partial=True, context={"company": period.company}
        )
        serializer.is_valid(raise_exception=True)
        branch = serializer.validated_data.get("branch")
        if branch is not None and branch.company_id != period.company_id:
            raise ValidationError({"branch_id": "La sucursal no pertenece a la empresa."})
        PeriodService.update(
            actor=request.user,
            period=period,
            context=get_request_context(request),
            **serializer.validated_data,
        )
        return period_detail_response(request, period)


class PeriodDueDateView(APIView):
    def post(self, request, period_id):
        period = get_period(period_id)
        require_period_capability(
            request,
            period,
            Cap.CHANGE_DUE_DATE,
            "Cambiar la fecha de vencimiento requiere rol Administrador o Supervisor/Aprobador.",
        )
        serializer = DueDateChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PeriodService.change_due_date(
            actor=request.user,
            period=period,
            new_due_at=serializer.to_due_at(period),
            reason=serializer.validated_data["reason"],
            context=get_request_context(request),
        )
        return period_detail_response(request, period)


class PeriodSubmitView(APIView):
    def post(self, request, period_id):
        period = get_period(period_id)
        require_period_capability(request, period, Cap.SUBMIT)
        PeriodService.submit(
            actor=request.user, period=period, context=get_request_context(request)
        )
        return period_detail_response(request, period)


class PeriodValidateView(APIView):
    def post(self, request, period_id):
        period = get_period(period_id)
        require_period_capability(
            request,
            period,
            Cap.VALIDATE,
            "Solo un Supervisor/Aprobador o Administrador puede validar el cierre.",
        )
        PeriodService.validate(
            actor=request.user, period=period, context=get_request_context(request)
        )
        return period_detail_response(request, period)


class PeriodReturnView(APIView):
    def post(self, request, period_id):
        period = get_period(period_id)
        require_period_capability(request, period, Cap.VALIDATE)
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PeriodService.return_to_preparation(
            actor=request.user,
            period=period,
            reason=serializer.validated_data["reason"],
            context=get_request_context(request),
        )
        return period_detail_response(request, period)


class PeriodHistoryView(APIView):
    def get(self, request, period_id):
        period = get_period(period_id)
        access_for_period(request, period)
        events = period.events.select_related("actor").order_by("created_at", "id")
        return Response(PeriodEventSerializer(events, many=True).data)


class PeriodDocumentsView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, period_id):
        period = get_period(period_id)
        access_for_period(request, period)
        documents = period.documents.exclude(status=Document.Status.DELETED).select_related(
            "uploaded_by", "rejected_by"
        )
        return Response(DocumentSerializer(documents, many=True).data)

    def post(self, request, period_id):
        period = get_period(period_id)
        require_period_capability(
            request, period, Cap.UPLOAD, "Su rol no tiene permiso para cargar documentos."
        )
        serializer = UploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = DocumentService.upload(
            actor=request.user,
            period=period,
            uploaded_file=serializer.validated_data["file"],
            context=get_request_context(request),
        )
        return Response(DocumentSerializer(document).data, status=status.HTTP_201_CREATED)


def get_document(document_id) -> Document:
    return get_object_or_404(
        Document.objects.select_related("period__company", "period__obligation"), pk=document_id
    )


class DocumentFileView(APIView):
    """Sirve el PDF solo a quien puede ver el período. `?download=1` lo
    entrega como adjunto; sin él, en línea para el visor del navegador."""

    def get(self, request, document_id):
        document = get_document(document_id)
        access_for_period(request, document.period)
        if document.status == Document.Status.DELETED:
            raise ValidationError({"detail": "El documento fue eliminado."})
        record_audit_event(
            actor=request.user,
            action="document.accessed",
            module="matriz",
            target=document,
            new_values={"download": request.query_params.get("download") == "1"},
            context=get_request_context(request),
        )
        response = FileResponse(
            document.file.open("rb"),
            content_type="application/pdf",
            as_attachment=request.query_params.get("download") == "1",
            filename=document.original_name,
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response


class DocumentRejectView(APIView):
    def post(self, request, document_id):
        document = get_document(document_id)
        require_period_capability(request, document.period, Cap.VALIDATE)
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = DocumentService.reject(
            actor=request.user,
            document=document,
            reason=serializer.validated_data["reason"],
            context=get_request_context(request),
        )
        return Response(DocumentSerializer(document).data)


class DocumentDeleteView(APIView):
    def delete(self, request, document_id):
        document = get_document(document_id)
        require_period_capability(request, document.period, Cap.UPLOAD)
        DocumentService.delete(
            actor=request.user, document=document, context=get_request_context(request)
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class CalendarView(APIView):
    def get(self, request, company_id):
        company = get_company(company_id)
        access = require_access(request, company)
        params = request.query_params
        today = timezone.localdate()
        try:
            year, month = int(params.get("year", today.year)), int(params.get("month", today.month))
            first = date(year, month, 1)
        except ValueError as exc:
            raise ValidationError({"month": "Año o mes inválido."}) from exc
        last = date(year + (month == 12), month % 12 + 1, 1)
        queryset = (
            visible_periods(access, request.user)
            .filter(due_at__date__gte=first, due_at__date__lt=last)
            .select_related(*PERIOD_RELATED)
            .order_by("due_at")
        )
        return Response(
            PeriodListSerializer(queryset, many=True, context={"now": timezone.now()}).data
        )


class DocumentsOverviewView(APIView):
    """Vista Documentos (5.12). Un período con solo documentos rechazados
    cuenta como pendiente (defecto 19 del mockup)."""

    def get(self, request, company_id):
        company = get_company(company_id)
        access = require_access(request, company)
        queryset = filtered_periods(request, access)
        context = {"now": timezone.now()}
        with_evidence = [period for period in queryset if period.valid_documents]
        pending = [period for period in queryset if not period.valid_documents]
        return Response(
            {
                "with_evidence": PeriodListSerializer(
                    with_evidence, many=True, context=context
                ).data,
                "pending": PeriodListSerializer(pending, many=True, context=context).data,
            }
        )


class ReportView(APIView):
    def get(self, request, company_id):
        company = get_company(company_id)
        access = require_access(request, company)
        queryset = filtered_periods(request, access)
        report = reports.compliance_report(queryset)
        export_format = request.query_params.get("export")
        if export_format:
            if not access.has(Cap.EXPORT):
                deny(request, "Su rol no permite exportar reportes.", capability=Cap.EXPORT)
            return export_response(
                request,
                company,
                export_format,
                title="Reporte de cumplimiento",
                headers=exports.REPORT_HEADERS,
                rows=exports.report_rows(report),
            )
        return Response(report)


class CompanyAuditView(APIView):
    """Historial de la empresa (Configuración → Auditoría), más reciente primero."""

    def get(self, request, company_id):
        company = get_company(company_id)
        require_capability(request, company, Cap.VIEW_AUDIT)
        params = request.query_params
        events = PeriodEvent.objects.filter(period__company=company).select_related(
            "actor", "period", "period__obligation"
        )
        if params.get("actor"):
            events = events.filter(actor_id=params["actor"])
        if params.get("action"):
            events = events.filter(action=params["action"])
        date_from, date_to = _parse_date(params.get("from"), "from"), _parse_date(
            params.get("to"), "to"
        )
        if date_from:
            events = events.filter(created_at__date__gte=date_from)
        if date_to:
            events = events.filter(created_at__date__lte=date_to)
        events = events.order_by("-created_at", "-id")
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(events, request, view=self)
        return paginator.get_paginated_response(AuditEventSerializer(page, many=True).data)
