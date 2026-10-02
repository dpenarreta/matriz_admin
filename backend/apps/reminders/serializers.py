from rest_framework import serializers

from .models import Notification, ReminderConfig


class ReminderConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReminderConfig
        fields = [
            "offsets",
            "send_time",
            "copy_backup",
            "escalation_enabled",
            "escalation_days",
            "escalation_repeat_days",
        ]

    def validate_offsets(self, value):
        if not isinstance(value, list) or any(
            not isinstance(item, int) or isinstance(item, bool) or not 0 <= item <= 90
            for item in value
        ):
            raise serializers.ValidationError("Cada anticipación debe ser un entero entre 0 y 90.")
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Las anticipaciones no pueden repetirse.")
        return sorted(set(value) | {0}, reverse=True)

    def validate_escalation_days(self, value):
        if not 1 <= value <= 30:
            raise serializers.ValidationError("Debe estar entre 1 y 30 días.")
        return value

    def validate_escalation_repeat_days(self, value):
        if value > 30:
            raise serializers.ValidationError("Debe estar entre 0 y 30 días.")
        return value


class NotificationSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    period_code = serializers.CharField(source="period.code", read_only=True)
    obligation_name = serializers.CharField(source="period.obligation.name", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "period",
            "period_code",
            "obligation_name",
            "kind",
            "kind_label",
            "offset_days",
            "recipient_email",
            "scheduled_for",
            "status",
            "status_label",
            "attempts",
            "last_error",
            "sent_at",
            "created_at",
        ]
        read_only_fields = fields
