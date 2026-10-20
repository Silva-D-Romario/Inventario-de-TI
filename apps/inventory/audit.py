import ipaddress
import uuid
from datetime import date, datetime, time
from decimal import Decimal

from django.db.models import Model

from apps.inventory.models import AuditLog


def normalize_audit_value(value):
    if isinstance(value, Model):
        return str(value.pk)
    if isinstance(value, dict):
        return {str(key): normalize_audit_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [normalize_audit_value(item) for item in value]
    if isinstance(value, date | datetime | time | Decimal | uuid.UUID):
        return str(value)
    if isinstance(value, bytes):
        return "<binary>"
    if hasattr(value, "name") and not isinstance(value, str):
        return str(value.name)
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def snapshot_fields(instance, field_names):
    return {
        field_name: normalize_audit_value(getattr(instance, field_name))
        for field_name in field_names
        if hasattr(instance, field_name)
    }


def audit_identity(instance):
    return {
        "resource_type": instance._meta.label_lower,
        "object_id": str(instance.pk),
        "object_repr": str(instance)[:255],
    }


def _request_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    candidate = forwarded_for.split(",", maxsplit=1)[0].strip()
    candidate = candidate or request.META.get("REMOTE_ADDR")
    try:
        return str(ipaddress.ip_address(candidate)) if candidate else None
    except ValueError:
        return None


def _request_id(request):
    try:
        return uuid.UUID(request.META.get("HTTP_X_REQUEST_ID", ""))
    except (ValueError, TypeError, AttributeError):
        return uuid.uuid4()


def record_audit(
    *,
    request,
    action,
    changes=None,
    instance=None,
    resource_type=None,
    object_id=None,
    object_repr=None,
):
    identity = audit_identity(instance) if instance is not None else {}
    return AuditLog.objects.create(
        actor=request.user if request.user.is_authenticated else None,
        action=action,
        resource_type=resource_type or identity["resource_type"],
        object_id=object_id or identity["object_id"],
        object_repr=object_repr or identity["object_repr"],
        changes=normalize_audit_value(changes or {}),
        ip_address=_request_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
        path=request.path[:255],
        method=request.method[:10],
        request_id=_request_id(request),
    )


class AuditTrailMixin:
    def get_create_save_kwargs(self):
        return {}

    def perform_create(self, serializer):
        instance = serializer.save(**self.get_create_save_kwargs())
        field_names = serializer.validated_data.keys()
        record_audit(
            request=self.request,
            action=AuditLog.Action.CREATE,
            instance=instance,
            changes={"fields": snapshot_fields(instance, field_names)},
        )

    def perform_update(self, serializer):
        field_names = tuple(serializer.validated_data.keys())
        before = snapshot_fields(serializer.instance, field_names)
        instance = serializer.save()
        after = snapshot_fields(instance, field_names)
        changes = {
            field_name: {"from": before[field_name], "to": after[field_name]}
            for field_name in field_names
            if before.get(field_name) != after.get(field_name)
        }
        record_audit(
            request=self.request,
            action=AuditLog.Action.UPDATE,
            instance=instance,
            changes=changes,
        )

    def perform_destroy(self, instance):
        identity = audit_identity(instance)
        instance.delete()
        record_audit(
            request=self.request,
            action=AuditLog.Action.DELETE,
            changes={},
            **identity,
        )
