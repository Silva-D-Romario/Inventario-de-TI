from django.contrib import admin

from apps.inventory.models import Asset, AssetStatus, Category, Sector


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
    list_display = ("asset_tag", "name", "category", "sector", "status", "updated_at")
    list_filter = ("category", "sector", "status")
    search_fields = ("asset_tag", "name", "serial_number", "manufacturer", "model")
    readonly_fields = ("created_by", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
