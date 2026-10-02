from datetime import datetime
from zoneinfo import ZoneInfo

from rest_framework import serializers

from apps.organizations.models import Area, Branch, ControlEntity, Membership
from apps.organizations.serializers import (
    AreaSerializer,
    BranchSerializer,
    ControlEntitySerializer,
    PersonSerializer,
    full_name,
)
from apps.users.models import User

from .models import Document, Obligation, Period, PeriodEvent, Priority
from .status import compute_status


class ObligationSerializer(serializers.ModelSerializer):
    area = AreaSerializer(read_only=True)
    control_entity = ControlEntitySerializer(read_only=True)
    type_label = serializers.CharField(source="get_type_display", read_only=True)
    periodicity_label = serializers.CharField(source="get_periodicity_display", read_only=True)

    class Meta:
        model = Obligation
        fields = [
            "id",
            "name",
            "description",
            "area",
            "control_entity",
            "type",
            "type_label",
            "periodicity",
            "periodicity_label",
            "legal_basis",
            "legal_basis_url",
            "expected_evidence",
            "due_day",
            "due_month",
            "due_time",
            "default_priority",
            "is_active",
        ]
        read_only_fields = fields


class CompanyScopedPersonField(serializers.PrimaryKeyRelatedField):
    """Usuario con membresía activa en la empresa del contexto: nadie puede
    asignar como responsable a una persona de otra empresa."""

    def get_queryset(self):
        company = self.context["company"]
        return User.objects.filter(
            is_active=True, memberships__company=company, memberships__is_active=True
        ).distinct()


class ObligationWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    area_id = serializers.PrimaryKeyRelatedField(queryset=Area.objects.all(), source="area")
    control_entity_id = serializers.PrimaryKeyRelatedField(
        queryset=ControlEntity.objects.all(), source="control_entity"
    )
    type = serializers.ChoiceField(choices=Obligation.Type.choices)
    periodicity = serializers.ChoiceField(choices=Obligation.Periodicity.choices)
    legal_basis = serializers.CharField(required=False, allow_blank=True, default="")
    legal_basis_url = serializers.URLField(required=False, allow_blank=True, default="")
    expected_evidence = serializers.CharField(max_length=255)
    due_day = serializers.IntegerField(min_value=1, max_value=31, required=False, allow_null=True)
    due_month = serializers.IntegerField(min_value=1, max_value=12, required=False, allow_null=True)
    due_time = serializers.TimeField(required=False)
    default_priority = serializers.ChoiceField(choices=Priority.choices, required=False)
    is_active = serializers.BooleanField(required=False)


class ObligationCreateSerializer(ObligationWriteSerializer):
    """Alta de obligación + su primer período (formulario 5.6)."""

    branch_id = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(), source="branch", required=False, allow_null=True
    )
    label = serializers.CharField(max_length=60, required=False, allow_blank=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    preparation_date = serializers.DateField(required=False, allow_null=True)
    due_date = serializers.DateField()
    responsible_id = CompanyScopedPersonField(source="responsible")
    backup_id = CompanyScopedPersonField(source="backup", required=False, allow_null=True)
    supervisor_id = CompanyScopedPersonField(source="supervisor", required=False, allow_null=True)
    approver_id = CompanyScopedPersonField(source="approver", required=False, allow_null=True)
    priority = serializers.ChoiceField(choices=Priority.choices, required=False)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    PERIOD_FIELDS = (
        "branch",
        "label",
        "start_date",
        "preparation_date",
        "due_date",
        "responsible",
        "backup",
        "supervisor",
        "approver",
        "priority",
        "notes",
    )

    def validate_branch_id(self, branch):
        if branch is not None and branch.company_id != self.context["company"].id:
            raise serializers.ValidationError("La sucursal no pertenece a la empresa.")
        return branch

    def validate(self, attrs):
        start, prep, due = attrs.get("start_date"), attrs.get("preparation_date"), attrs["due_date"]
        if start and start > due:
            raise serializers.ValidationError(
                {"start_date": "No puede ser posterior al vencimiento."}
            )
        if prep and prep > due:
            raise serializers.ValidationError(
                {"preparation_date": "No puede ser posterior al vencimiento."}
            )
        if start and prep and start > prep:
            raise serializers.ValidationError(
                {"preparation_date": "No puede ser anterior a la fecha de inicio."}
            )
        return attrs

    def split(self) -> tuple[dict, dict]:
        data = dict(self.validated_data)
        period = {key: data.pop(key) for key in self.PERIOD_FIELDS if key in data}
        if "due_time" in data:
            period["due_time"] = data["due_time"]
        if not period.get("label"):
            period.pop("label", None)
        return data, period


class PeriodUpdateSerializer(serializers.Serializer):
    responsible_id = CompanyScopedPersonField(source="responsible", required=False)
    backup_id = CompanyScopedPersonField(source="backup", required=False, allow_null=True)
    supervisor_id = CompanyScopedPersonField(source="supervisor", required=False, allow_null=True)
    approver_id = CompanyScopedPersonField(source="approver", required=False, allow_null=True)
    priority = serializers.ChoiceField(choices=Priority.choices, required=False)
    progress = serializers.IntegerField(min_value=0, max_value=100, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    branch_id = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(), source="branch", required=False, allow_null=True
    )


class DueDateChangeSerializer(serializers.Serializer):
    due_date = serializers.DateField()
    due_time = serializers.TimeField(required=False)
    reason = serializers.CharField()

    def to_due_at(self, period: Period) -> datetime:
        tz = ZoneInfo(period.company.timezone)
        due_time = self.validated_data.get("due_time") or period.due_at.astimezone(tz).time()
        return datetime.combine(self.validated_data["due_date"], due_time, tzinfo=tz)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField()


class UploadSerializer(serializers.Serializer):
    file = serializers.FileField()


def _person(user):
    return PersonSerializer(user).data if user else None


class PeriodListSerializer(serializers.ModelSerializer):
    """Fila de la matriz. El estado se calcula con `compute_status` usando
    la hora de la petición (`context["now"]`), igual para todas las filas."""

    obligation_id = serializers.IntegerField(source="obligation.id")
    obligation_name = serializers.CharField(source="obligation.name")
    area = serializers.SerializerMethodField()
    control_entity = serializers.SerializerMethodField()
    responsible = serializers.SerializerMethodField()
    priority_label = serializers.CharField(source="get_priority_display")
    stage_label = serializers.CharField(source="get_stage_display")
    status = serializers.SerializerMethodField()
    valid_document_count = serializers.SerializerMethodField()

    class Meta:
        model = Period
        fields = [
            "id",
            "code",
            "label",
            "obligation_id",
            "obligation_name",
            "area",
            "control_entity",
            "responsible",
            "priority",
            "priority_label",
            "progress",
            "stage",
            "stage_label",
            "due_at",
            "is_closed",
            "status",
            "valid_document_count",
        ]
        read_only_fields = fields

    def get_area(self, obj):
        return {
            "id": obj.obligation.area_id,
            "code": obj.obligation.area.code,
            "name": obj.obligation.area.name,
        }

    def get_control_entity(self, obj):
        entity = obj.obligation.control_entity
        return {"id": entity.id, "code": entity.code, "name": entity.name}

    def get_responsible(self, obj):
        return {"id": obj.responsible_id, "full_name": full_name(obj.responsible)}

    def get_status(self, obj):
        return compute_status(obj, self.context.get("now")).as_dict()

    def get_valid_document_count(self, obj) -> int:
        annotated = getattr(obj, "valid_documents", None)
        if annotated is not None:
            return annotated
        return obj.documents.filter(status=Document.Status.VALID).count()


class PeriodDetailSerializer(PeriodListSerializer):
    obligation = ObligationSerializer(read_only=True)
    branch = BranchSerializer(read_only=True)
    backup = serializers.SerializerMethodField()
    supervisor = serializers.SerializerMethodField()
    approver = serializers.SerializerMethodField()
    submitted_by = serializers.SerializerMethodField()
    validated_by = serializers.SerializerMethodField()
    responsible = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()

    class Meta(PeriodListSerializer.Meta):
        fields = PeriodListSerializer.Meta.fields + [
            "obligation",
            "company",
            "branch",
            "start_date",
            "preparation_date",
            "backup",
            "supervisor",
            "approver",
            "notes",
            "submitted_at",
            "submitted_by",
            "completed_at",
            "validated_at",
            "validated_by",
            "reminders_suspended",
            "actions",
        ]
        read_only_fields = fields

    def get_responsible(self, obj):
        return _person(obj.responsible)

    def get_backup(self, obj):
        return _person(obj.backup)

    def get_supervisor(self, obj):
        return _person(obj.supervisor)

    def get_approver(self, obj):
        return _person(obj.approver)

    def get_submitted_by(self, obj):
        return _person(obj.submitted_by)

    def get_validated_by(self, obj):
        return _person(obj.validated_by)

    def get_company(self, obj):
        return {
            "id": obj.company_id,
            "code": obj.company.code,
            "short_name": obj.company.short_name,
            "timezone": obj.company.timezone,
        }

    def get_actions(self, obj):
        return self.context.get("actions", {})


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.SerializerMethodField()
    rejected_by = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "original_name",
            "version",
            "size",
            "content_type",
            "sha256",
            "status",
            "status_label",
            "rejection_reason",
            "rejected_by",
            "rejected_at",
            "uploaded_by",
            "created_at",
        ]
        read_only_fields = fields

    def get_uploaded_by(self, obj):
        return _person(obj.uploaded_by)

    def get_rejected_by(self, obj):
        return _person(obj.rejected_by)


class PeriodEventSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()

    class Meta:
        model = PeriodEvent
        fields = [
            "id",
            "created_at",
            "actor",
            "action",
            "description",
            "reason",
            "previous_value",
            "new_value",
        ]
        read_only_fields = fields

    def get_actor(self, obj):
        return full_name(obj.actor) if obj.actor else "Sistema"


class AuditEventSerializer(PeriodEventSerializer):
    period_code = serializers.CharField(source="period.code")
    period_label = serializers.CharField(source="period.label")
    obligation_name = serializers.CharField(source="period.obligation.name")

    class Meta(PeriodEventSerializer.Meta):
        fields = PeriodEventSerializer.Meta.fields + [
            "period_code",
            "period_label",
            "obligation_name",
        ]
        read_only_fields = fields


def catalog_choices() -> dict:
    return {
        "types": [{"value": v, "label": label} for v, label in Obligation.Type.choices],
        "periodicities": [
            {"value": v, "label": label} for v, label in Obligation.Periodicity.choices
        ],
        "priorities": [{"value": v, "label": label} for v, label in Priority.choices],
        "stages": [{"value": v, "label": label} for v, label in Period.Stage.choices],
        "roles": [{"value": v, "label": label} for v, label in Membership.Role.choices],
    }
