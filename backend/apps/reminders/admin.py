from django.contrib import admin

from .models import Notification, ReminderConfig


@admin.register(ReminderConfig)
class ReminderConfigAdmin(admin.ModelAdmin):
    list_display = ("company", "offsets", "send_time", "escalation_enabled", "escalation_days")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("period", "kind", "recipient_email", "scheduled_for", "status", "attempts")
    list_filter = ("kind", "status")
    search_fields = ("period__code", "recipient_email")

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in Notification._meta.fields]
