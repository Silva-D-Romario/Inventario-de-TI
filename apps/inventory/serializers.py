from django.utils import timezone
from rest_framework import serializers

from apps.inventory.models import Asset, AssetStatus, Category, Sector


class CaseInsensitiveNameMixin:
    def validate_name(self, value):
        normalized = value.strip()
        queryset = self.Meta.model.objects.filter(name__iexact=normalized)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Já existe um cadastro com este nome.")
        return normalized


class CategorySerializer(CaseInsensitiveNameMixin, serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "description", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class SectorSerializer(CaseInsensitiveNameMixin, serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ("id", "name", "location", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class AssetStatusSerializer(CaseInsensitiveNameMixin, serializers.ModelSerializer):
    class Meta:
        model = AssetStatus
        fields = ("id", "code", "name", "color", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_code(self, value):
        normalized = value.strip().lower()
        queryset = AssetStatus.objects.filter(code__iexact=normalized)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Já existe um status com este código.")
        return normalized


class AssetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    sector_name = serializers.CharField(source="sector.name", read_only=True)
    status_name = serializers.CharField(source="status.name", read_only=True)
    status_color = serializers.CharField(source="status.color", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = Asset
        fields = (
            "id",
            "asset_tag",
            "name",
            "category",
            "category_name",
            "sector",
            "sector_name",
            "status",
            "status_name",
            "status_color",
            "serial_number",
            "manufacturer",
            "model",
            "acquisition_date",
            "purchase_value",
            "notes",
            "created_by_username",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by_username", "created_at", "updated_at")

    def validate_asset_tag(self, value):
        normalized = value.strip().upper()
        queryset = Asset.objects.filter(asset_tag__iexact=normalized)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Já existe um ativo com este patrimônio.")
        return normalized

    def validate_serial_number(self, value):
        if not value or not value.strip():
            return None
        normalized = value.strip()
        queryset = Asset.objects.filter(serial_number__iexact=normalized)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Já existe um ativo com este número de série.")
        return normalized

    def validate_acquisition_date(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError("A data de aquisição não pode estar no futuro.")
        return value
