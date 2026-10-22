from django.contrib import admin

from apps.inventory.models import (
    Asset,
    AssetAttachment,
    AssetCost,
    AssetMovement,
    AssetStatus,
    AuditLog,
    Category,
    Loan,
    Maintenance,
    Notification,
    ResponsiblePerson,
    Sector,
    Warranty,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "location")


@admin.register(AssetStatus)
class AssetStatusAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "color", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = (
        "asset_tag",
        "name",
        "category",
        "sector",
        "status",
        "responsible",
        "updated_at",
    )
    list_filter = ("category", "sector", "status")
    search_fields = ("asset_tag", "public_id", "name", "serial_number", "manufacturer", "model")
    readonly_fields = ("public_id", "created_by", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ResponsiblePerson)
class ResponsiblePersonAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "employee_id", "sector", "is_active")
    list_filter = ("is_active", "sector")
    search_fields = ("name", "email", "employee_id")


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        "asset",
        "borrower",
        "loaned_at",
        "expected_return_date",
        "returned_at",
    )
    list_filter = ("loaned_at", "returned_at")
    search_fields = ("asset__asset_tag", "asset__name", "borrower__name")
    readonly_fields = ("created_by", "created_at", "updated_at")


@admin.register(AssetMovement)
class AssetMovementAdmin(admin.ModelAdmin):
    list_display = ("asset", "movement_type", "from_sector", "to_sector", "created_at")
    list_filter = ("movement_type", "from_sector", "to_sector")
    search_fields = ("asset__asset_tag", "asset__name", "responsible__name")
    readonly_fields = (
        "asset",
        "movement_type",
        "from_sector",
        "to_sector",
        "responsible",
        "loan",
        "maintenance",
        "performed_by",
        "notes",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Maintenance)
class MaintenanceAdmin(admin.ModelAdmin):
    list_display = (
        "asset",
        "maintenance_type",
        "status",
        "started_at",
        "completed_at",
        "cost",
    )
    list_filter = ("maintenance_type", "status", "started_at")
    search_fields = ("asset__asset_tag", "asset__name", "description", "provider")
    readonly_fields = ("created_by", "created_at", "updated_at")


@admin.register(Warranty)
class WarrantyAdmin(admin.ModelAdmin):
    list_display = ("asset", "provider", "contract_number", "start_date", "end_date")
    list_filter = ("start_date", "end_date")
    search_fields = ("asset__asset_tag", "asset__name", "provider", "contract_number")
    readonly_fields = ("created_by", "created_at", "updated_at")


@admin.register(AssetCost)
class AssetCostAdmin(admin.ModelAdmin):
    list_display = ("asset", "cost_type", "amount", "occurred_on", "maintenance")
    list_filter = ("cost_type", "occurred_on")
    search_fields = ("asset__asset_tag", "asset__name", "description")
    readonly_fields = ("created_by", "created_at", "updated_at")


@admin.register(AssetAttachment)
class AssetAttachmentAdmin(admin.ModelAdmin):
    list_display = ("asset", "description", "maintenance", "uploaded_by", "created_at")
    search_fields = ("asset__asset_tag", "asset__name", "description")
    readonly_fields = ("uploaded_by", "created_at", "updated_at")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "resource_type", "object_repr")
    list_filter = ("action", "resource_type", "created_at")
    search_fields = ("actor__username", "object_id", "object_repr", "path")
    readonly_fields = (
        "actor",
        "action",
        "resource_type",
        "object_id",
        "object_repr",
        "changes",
        "ip_address",
        "user_agent",
        "path",
        "method",
        "request_id",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "recipient", "alert_type", "title", "read_at")
    list_filter = ("alert_type", "read_at", "created_at")
    search_fields = ("recipient__username", "recipient__email", "title", "message")
    readonly_fields = (
        "recipient",
        "alert_type",
        "title",
        "message",
        "resource_type",
        "resource_id",
        "dedup_key",
        "read_at",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
