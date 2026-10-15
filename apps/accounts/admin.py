from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.accounts.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = (*UserAdmin.fieldsets, ("Acesso", {"fields": ("role",)}))
    add_fieldsets = (*UserAdmin.add_fieldsets, ("Acesso", {"fields": ("email", "role")}))
    list_display = ("username", "email", "first_name", "last_name", "role", "is_active")
    list_filter = (*UserAdmin.list_filter, "role")
    search_fields = ("username", "email", "first_name", "last_name")
