"""Lógica de negocio de obligaciones, períodos y evidencias.

Las vistas solo validan forma y permisos; toda regla de negocio (requisitos
para enviar o validar, separación de funciones, justificación del cambio de
fecha, validación del PDF) vive aquí, para que ningún camino alternativo
(otra vista, un comando, el admin) pueda saltársela.
"""

import hashlib
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.audit import record_audit_event
from apps.organizations.models import Company
from apps.users.models import User

from .models import Document, Obligation, Period, PeriodEvent
from .scheduling import (
    default_dates,
    first_due_date,
    local_due_datetime,
    next_code,
    next_due_date,
    period_label,
)

PDF_MAGIC = b"%PDF-"
FIELD_LABELS = {
    "responsible": "responsable",
    "backup": "suplente",
    "supervisor": "supervisor",
    "approver": "aprobador",
    "priority": "prioridad",
    "progress": "avance",
    "notes": "observaciones",
    "branch": "sucursal",
}
MIN_REASON_LENGTH = 10


def _display(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, User):
        return value.get_full_name() or value.username
    if isinstance(value, datetime):
        return timezone.localtime(value).strftime("%Y-%m-%d %H:%M")
    return str(value)


def record_event(
    period: Period,
    *,
    actor: User | None,
    action: str,
    description: str,
    reason: str = "",
    previous_value: str = "",
    new_value: str = "",
) -> PeriodEvent:
    return PeriodEvent.objects.create(
        period=period,
        actor=actor,
        action=action,
        description=description[:255],
        reason=reason,
        previous_value=previous_value[:255],
        new_value=new_value[:255],
    )


class PeriodService:
    @staticmethod
    @transaction.atomic
    def create_period(
        *,
        obligation: Obligation,
        due: date,
        responsible: User,
        actor: User | None = None,
        backup: User | None = None,
        supervisor: User | None = None,
        approver: User | None = None,
        priority: str | None = None,
        branch=None,
        label: str | None = None,
        start_date: date | None = None,
        preparation_date: date | None = None,
        due_time=None,
        notes: str = "",
        description: str = "Registro del período generado",
    ) -> Period:
        company = obligation.company
        default_start, default_preparation = default_dates(due)
        start_date = start_date or default_start
        preparation_date = preparation_date or default_preparation
        if not (start_date <= preparation_date <= due):
            raise ValidationError(
                {"start_date": "Debe cumplirse: inicio ≤ preparación interna ≤ vencimiento."}
            )
        period = Period.objects.create(
            code=next_code(),
            obligation=obligation,
            company=company,
            branch=branch,
            label=label or period_label(obligation.periodicity, due),
            start_date=start_date,
            preparation_date=preparation_date,
            due_at=local_due_datetime(company, due, due_time or obligation.due_time),
            responsible=responsible,
            backup=backup,
            supervisor=supervisor,
            approver=approver or company.general_manager,
            priority=priority or obligation.default_priority,
            notes=notes,
        )
        record_event(
            period,
            actor=actor,
            action="period.created",
            description=description,
            reason=f"Periodicidad {obligation.get_periodicity_display().lower()}",
        )
        return period

    EDITABLE_FIELDS = (
        "responsible",
        "backup",
        "supervisor",
        "approver",
        "priority",
        "progress",
        "notes",
        "branch",
    )

    @staticmethod
    @transaction.atomic
    def update(*, actor: User, period: Period, context=None, **fields) -> Period:
        if period.is_closed:
            raise ValidationError({"detail": "Un período cerrado no se puede editar."})
        if "responsible" in fields and fields["responsible"] is None:
            raise ValidationError({"responsible_id": "El responsable es obligatorio."})
        changes = []
        for name in PeriodService.EDITABLE_FIELDS:
            if name not in fields:
                continue
            value, current = fields[name], getattr(period, name)
            if value == current:
                continue
            changes.append((name, _display(current), _display(value)))
            setattr(period, name, value)
        if not changes:
            return period
        period.save()
        for name, before, after in changes:
            label = FIELD_LABELS[name]
            record_event(
                period,
                actor=actor,
                action="period.updated",
                description=f"Cambio de {label}",
                previous_value=before,
                new_value=after,
            )
        record_audit_event(
            actor=actor,
            action="period.updated",
            module="matriz",
            target=period,
            previous_values={name: before for name, before, _ in changes},
            new_values={name: after for name, _, after in changes},
            context=context,
        )
        return period

    @staticmethod
    @transaction.atomic
    def change_due_date(
        *, actor: User, period: Period, new_due_at: datetime, reason: str, context=None
    ) -> Period:
        reason = (reason or "").strip()
        if period.is_closed:
            raise ValidationError({"detail": "No se cambia la fecha de un período cerrado."})
        if len(reason) < MIN_REASON_LENGTH:
            raise ValidationError(
                {
                    "reason": f"La justificación es obligatoria (mínimo {MIN_REASON_LENGTH} caracteres)."
                }
            )
        local_new = timezone.localtime(new_due_at, ZoneInfo(period.company.timezone)).date()
        if local_new < period.start_date:
            raise ValidationError(
                {"due_at": "El vencimiento no puede ser anterior a la fecha de inicio."}
            )
        previous = period.due_at
        period.due_at = new_due_at
        period.save(update_fields=["due_at", "updated_at"])
        record_event(
            period,
            actor=actor,
            action="period.due_date_changed",
            description="Cambio de fecha de vencimiento",
            reason=reason,
            previous_value=_display(previous),
            new_value=_display(new_due_at),
        )
        record_audit_event(
            actor=actor,
            action="period.due_date_changed",
            module="matriz",
            target=period,
            previous_values={"due_at": previous.isoformat()},
            new_values={"due_at": new_due_at.isoformat(), "reason": reason},
            context=context,
        )
        return period

    @staticmethod
    def _valid_documents(period: Period):
        return period.documents.filter(status=Document.Status.VALID)

    @staticmethod
    @transaction.atomic
    def submit(*, actor: User, period: Period, context=None) -> Period:
        period = Period.objects.select_for_update().get(pk=period.pk)
        if period.is_closed:
            raise ValidationError({"detail": "El período ya está cerrado."})
        if period.stage == Period.Stage.PENDING_VALIDATION:
            raise ValidationError({"detail": "El período ya está pendiente de validación."})
        if not PeriodService._valid_documents(period).exists():
            raise ValidationError(
                {
                    "detail": "Debe cargar la evidencia requerida "
                    f"({period.obligation.expected_evidence}) antes de enviar a validación."
                }
            )
        period.stage = Period.Stage.PENDING_VALIDATION
        period.progress = max(period.progress, 95)
        period.submitted_at = timezone.now()
        period.submitted_by = actor
        period.save()
        record_event(
            period, actor=actor, action="period.submitted", description="Enviado a validación"
        )
        record_audit_event(
            actor=actor, action="period.submitted", module="matriz", target=period, context=context
        )
        return period

    @staticmethod
    @transaction.atomic
    def validate(*, actor: User, period: Period, context=None) -> Period:
        period = Period.objects.select_for_update().select_related("company").get(pk=period.pk)
        if period.is_closed:
            raise ValidationError({"detail": "El período ya está cerrado."})
        if period.stage != Period.Stage.PENDING_VALIDATION:
            raise ValidationError({"detail": "Solo se valida un período pendiente de validación."})
        valid_documents = PeriodService._valid_documents(period)
        if not valid_documents.exists():
            raise ValidationError({"detail": "No se puede finalizar sin evidencia válida cargada."})
        # Separación de funciones (defecto 6 del mockup): quien envió o cargó
        # la evidencia no valida su propio cierre.
        if period.submitted_by_id == actor.pk or valid_documents.filter(uploaded_by=actor).exists():
            raise PermissionDenied(
                "Separación de funciones: quien cargó la evidencia o envió el período "
                "no puede validar ese mismo cierre."
            )
        now = timezone.now()
        basis = period.company.compliance_date_basis
        period.completed_at = (
            period.submitted_at
            if basis == Company.ComplianceDateBasis.SUBMISSION and period.submitted_at
            else now
        )
        period.validated_at = now
        period.validated_by = actor
        period.is_closed = True
        period.progress = 100
        period.reminders_suspended = True
        period.save()
        late = period.completed_at > period.due_at
        record_event(
            period,
            actor=actor,
            action="period.validated",
            description="Cierre validado" + (" — Finalizada fuera de plazo" if late else ""),
            reason="Se conserva el atraso para efectos de reportes." if late else "",
        )
        record_audit_event(
            actor=actor,
            action="period.validated",
            module="matriz",
            target=period,
            new_values={"late": late},
            context=context,
        )
        return period

    @staticmethod
    @transaction.atomic
    def return_to_preparation(*, actor: User, period: Period, reason: str, context=None) -> Period:
        reason = (reason or "").strip()
        if period.is_closed or period.stage != Period.Stage.PENDING_VALIDATION:
            raise ValidationError(
                {"detail": "Solo se devuelve un período pendiente de validación."}
            )
        if len(reason) < MIN_REASON_LENGTH:
            raise ValidationError(
                {"reason": f"El motivo es obligatorio (mínimo {MIN_REASON_LENGTH} caracteres)."}
            )
        period.stage = Period.Stage.IN_PREPARATION
        period.progress = min(period.progress, 50)
        period.submitted_at = None
        period.submitted_by = None
        period.save()
        record_event(
            period,
            actor=actor,
            action="period.returned",
            description="Devuelto a preparación",
            reason=reason,
        )
        record_audit_event(
            actor=actor,
            action="period.returned",
            module="matriz",
            target=period,
            new_values={"reason": reason},
            context=context,
        )
        return period


class ObligationService:
    @staticmethod
    @transaction.atomic
    def create(
        *, actor: User, company: Company, obligation_data: dict, period_data: dict, context=None
    ):
        name = obligation_data["name"].strip()
        if Obligation.objects.filter(company=company, name__iexact=name).exists():
            raise ValidationError(
                {"name": "Ya existe una obligación con ese nombre en la empresa."}
            )
        obligation = Obligation.objects.create(
            company=company, created_by=actor, **{**obligation_data, "name": name}
        )
        due = period_data.pop("due_date", None) or first_due_date(obligation, timezone.localdate())
        period = PeriodService.create_period(
            obligation=obligation,
            due=due,
            actor=actor,
            description="Obligación creada",
            **period_data,
        )
        record_audit_event(
            actor=actor,
            action="obligation.created",
            module="matriz",
            target=obligation,
            new_values={"name": name, "company": company.code, "period": period.code},
            context=context,
        )
        return obligation, period

    EDITABLE_FIELDS = (
        "name",
        "description",
        "area",
        "control_entity",
        "type",
        "periodicity",
        "legal_basis",
        "legal_basis_url",
        "expected_evidence",
        "due_day",
        "due_month",
        "due_time",
        "default_priority",
        "is_active",
    )

    @staticmethod
    def update(*, actor: User, obligation: Obligation, context=None, **fields) -> Obligation:
        previous, new = {}, {}
        for name in ObligationService.EDITABLE_FIELDS:
            if name in fields and fields[name] != getattr(obligation, name):
                previous[name], new[name] = _display(getattr(obligation, name)), _display(
                    fields[name]
                )
                setattr(obligation, name, fields[name])
        if "name" in new and (
            Obligation.objects.filter(company=obligation.company, name__iexact=obligation.name)
            .exclude(pk=obligation.pk)
            .exists()
        ):
            raise ValidationError(
                {"name": "Ya existe una obligación con ese nombre en la empresa."}
            )
        if new:
            obligation.save()
            record_audit_event(
                actor=actor,
                action="obligation.updated",
                module="matriz",
                target=obligation,
                previous_values=previous,
                new_values=new,
                context=context,
            )
        return obligation


class DocumentService:
    @staticmethod
    def _validate_pdf(uploaded_file) -> bytes:
        max_bytes = settings.DOCUMENT_MAX_UPLOAD_MB * 1024 * 1024
        name = uploaded_file.name or ""
        if not name.lower().endswith(".pdf"):
            raise ValidationError({"file": "Formato no permitido. Solo se aceptan archivos PDF."})
        if uploaded_file.size > max_bytes:
            raise ValidationError(
                {
                    "file": f"Supera el tamaño máximo permitido ({settings.DOCUMENT_MAX_UPLOAD_MB} MB)."
                }
            )
        content = uploaded_file.read()
        # La extensión no basta (defecto 11 del mockup): se exige la firma
        # de un PDF real al inicio del contenido.
        if not content.startswith(PDF_MAGIC):
            raise ValidationError({"file": "El archivo no es un PDF válido."})
        return content

    @staticmethod
    @transaction.atomic
    def upload(*, actor: User, period: Period, uploaded_file, context=None) -> Document:
        if period.is_closed:
            raise ValidationError({"detail": "No se cargan documentos en un período cerrado."})
        content = DocumentService._validate_pdf(uploaded_file)
        from django.core.files.base import ContentFile

        version = period.documents.filter(original_name__iexact=uploaded_file.name).count() + 1
        document = Document(
            period=period,
            original_name=uploaded_file.name[:255],
            version=version,
            size=len(content),
            content_type="application/pdf",
            sha256=hashlib.sha256(content).hexdigest(),
            uploaded_by=actor,
        )
        document.file.save(uploaded_file.name, ContentFile(content), save=False)
        document.save()
        if period.stage == Period.Stage.NOT_STARTED:
            period.stage = Period.Stage.IN_PREPARATION
            period.progress = max(period.progress, 25)
            period.save(update_fields=["stage", "progress", "updated_at"])
        record_event(
            period,
            actor=actor,
            action="document.uploaded",
            description=f"Evidencia cargada: {document.original_name} (v{version})",
        )
        record_audit_event(
            actor=actor,
            action="document.uploaded",
            module="matriz",
            target=document,
            new_values={
                "period": period.code,
                "name": document.original_name,
                "sha256": document.sha256,
            },
            context=context,
        )
        return document

    @staticmethod
    @transaction.atomic
    def reject(*, actor: User, document: Document, reason: str, context=None) -> Document:
        reason = (reason or "").strip()
        if document.status != Document.Status.VALID:
            raise ValidationError({"detail": "Solo se rechaza un documento válido."})
        if len(reason) < MIN_REASON_LENGTH:
            raise ValidationError(
                {"reason": f"El motivo es obligatorio (mínimo {MIN_REASON_LENGTH} caracteres)."}
            )
        document.status = Document.Status.REJECTED
        document.rejection_reason = reason
        document.rejected_by = actor
        document.rejected_at = timezone.now()
        document.save()
        record_event(
            document.period,
            actor=actor,
            action="document.rejected",
            description=f"Evidencia rechazada: {document.original_name}",
            reason=reason,
        )
        record_audit_event(
            actor=actor,
            action="document.rejected",
            module="matriz",
            target=document,
            new_values={"reason": reason},
            context=context,
        )
        return document

    @staticmethod
    @transaction.atomic
    def delete(*, actor: User, document: Document, context=None) -> Document:
        """Solo se eliminan documentos rechazados, y se marcan (no se borra el
        archivo): el expediente conserva todo lo que se cargó."""
        if document.status != Document.Status.REJECTED:
            raise ValidationError({"detail": "Solo se eliminan documentos rechazados."})
        document.status = Document.Status.DELETED
        document.deleted_by = actor
        document.deleted_at = timezone.now()
        document.save()
        record_event(
            document.period,
            actor=actor,
            action="document.deleted",
            description=f"Documento rechazado eliminado: {document.original_name}",
        )
        record_audit_event(
            actor=actor,
            action="document.deleted",
            module="matriz",
            target=document,
            context=context,
        )
        return document


class GenerationService:
    """Crea los períodos siguientes de las obligaciones recurrentes activas.
    Idempotente: si el siguiente período ya existe, no hace nada."""

    MAX_PERIODS_PER_RUN = 24

    @staticmethod
    def generate(now: datetime | None = None) -> list[Period]:
        now = now or timezone.now()
        horizon = now + timedelta(days=settings.PERIOD_GENERATION_LEAD_DAYS)
        created = []
        recurring = Obligation.objects.filter(is_active=True, company__is_active=True).exclude(
            periodicity=Obligation.Periodicity.ONCE
        )
        for obligation in recurring.select_related("company"):
            for _ in range(GenerationService.MAX_PERIODS_PER_RUN):
                latest = obligation.periods.order_by("-due_at").first()
                if latest is None or latest.due_at > horizon:
                    break
                latest_due = timezone.localtime(
                    latest.due_at, ZoneInfo(obligation.company.timezone)
                ).date()
                due = next_due_date(obligation, latest_due)
                if due is None:
                    break
                label = period_label(obligation.periodicity, due)
                if obligation.periods.filter(label=label).exists():
                    break
                created.append(
                    PeriodService.create_period(
                        obligation=obligation,
                        due=due,
                        responsible=latest.responsible,
                        backup=latest.backup,
                        supervisor=latest.supervisor,
                        approver=latest.approver,
                        priority=latest.priority,
                        branch=latest.branch,
                        label=label,
                    )
                )
        return created
