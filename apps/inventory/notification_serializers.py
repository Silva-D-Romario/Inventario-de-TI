from rest_framework import serializers

from apps.inventory.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    alert_type_display = serializers.CharField(source="get_alert_type_display", read_only=True)
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "alert_type",
            "alert_type_display",
            "title",
            "message",
            "resource_type",
            "resource_id",
            "is_read",
            "read_at",
            "created_at",
        )
        read_only_fields = fields


class MarkAllNotificationsReadSerializer(serializers.Serializer):
    updated = serializers.IntegerField()
