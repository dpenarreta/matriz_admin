from django.contrib import admin

from .models import Document, Obligation, Period, PeriodEvent


@admin.register(Obligation)
class ObligationAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "area", "control_entity", "periodicity", "is_active")
    list_filter = ("company", "area", "control_entity", "periodicity", "is_active")
    search_fields = ("name",)


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 0
    fields = ("original_name", "version", "status", "uploaded_by", "created_at")
    readonly_fields = fields
    can_delete = False


class PeriodEventInline(admin.TabularInline):
    model = PeriodEvent
    extra = 0
    fields = ("created_at", "actor", "description", "reason", "previous_value", "new_value")
    readonly_fields = fields
    can_delete = False


@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = ("code", "obligation", "label", "due_at", "responsible", "stage", "is_closed")
    list_filter = ("company", "stage", "is_closed", "priority")
    search_fields = ("code", "obligation__name", "label")
    inlines = [DocumentInline, PeriodEventInline]
    # El historial y los cierres se gestionan solo por la API (con sus reglas).
    readonly_fields = (
        "is_closed",
        "completed_at",
        "validated_at",
        "validated_by",
        "submitted_at",
        "submitted_by",
    )
