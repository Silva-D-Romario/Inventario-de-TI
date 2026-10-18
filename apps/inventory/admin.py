from django.contrib import admin

from apps.inventory.models import (
    Asset,
    AssetMovement,
    AssetStatus,
    Category,
    Loan,
    ResponsiblePerson,
    Sector,
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
    search_fields = ("asset_tag", "name", "serial_number", "manufacturer", "model")
    readonly_fields = ("created_by", "created_at", "updated_at")

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
        "performed_by",
        "notes",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
