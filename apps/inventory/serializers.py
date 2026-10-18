from django.utils import timezone
from rest_framework import serializers

from apps.inventory.models import (
    Asset,
    AssetMovement,
    AssetStatus,
    Category,
    Loan,
    ResponsiblePerson,
    Sector,
)
from apps.inventory.services import (
    InventoryOperationError,
    create_loan,
    transfer_asset,
)


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
    responsible_name = serializers.CharField(source="responsible.name", read_only=True)

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
            "responsible",
            "responsible_name",
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
        read_only_fields = (
            "id",
            "responsible",
            "responsible_name",
            "created_by_username",
            "created_at",
            "updated_at",
        )

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

    def validate(self, attrs):
        if self.instance and "sector" in attrs and attrs["sector"] != self.instance.sector:
            raise serializers.ValidationError(
                {"sector": "Use a operação de transferência para alterar o setor."}
            )
        return attrs


class ResponsiblePersonSerializer(serializers.ModelSerializer):
    sector_name = serializers.CharField(source="sector.name", read_only=True)

    class Meta:
        model = ResponsiblePerson
        fields = (
            "id",
            "name",
            "email",
            "employee_id",
            "phone",
            "sector",
            "sector_name",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_employee_id(self, value):
        return value.strip() if value and value.strip() else None

    def validate_email(self, value):
        normalized = value.strip().lower()
        queryset = ResponsiblePerson.objects.filter(email__iexact=normalized)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Já existe um responsável com este e-mail.")
        return normalized


class LoanSerializer(serializers.ModelSerializer):
    asset_tag = serializers.CharField(source="asset.asset_tag", read_only=True)
    borrower_name = serializers.CharField(source="borrower.name", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Loan
        fields = (
            "id",
            "asset",
            "asset_tag",
            "borrower",
            "borrower_name",
            "loaned_at",
            "expected_return_date",
            "returned_at",
            "is_active",
            "notes",
            "created_by_username",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "returned_at",
            "is_active",
            "created_by_username",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        loaned_at = attrs.get("loaned_at", timezone.localdate())
        if loaned_at > timezone.localdate():
            raise serializers.ValidationError(
                {"loaned_at": "A data do empréstimo não pode estar no futuro."}
            )
        if attrs["expected_return_date"] < loaned_at:
            raise serializers.ValidationError(
                {"expected_return_date": "A devolução prevista não pode anteceder o empréstimo."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.setdefault("loaned_at", timezone.localdate())
        validated_data.setdefault("notes", "")
        try:
            return create_loan(user=self.context["request"].user, **validated_data)
        except InventoryOperationError as error:
            raise serializers.ValidationError({"detail": str(error)}) from error


class ReturnLoanSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class TransferAssetSerializer(serializers.Serializer):
    to_sector = serializers.PrimaryKeyRelatedField(queryset=Sector.objects.filter(is_active=True))
    responsible = serializers.PrimaryKeyRelatedField(
        queryset=ResponsiblePerson.objects.filter(is_active=True),
        allow_null=True,
        required=True,
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def save(self, **kwargs):
        try:
            asset, movement = transfer_asset(
                asset=self.context["asset"],
                user=self.context["request"].user,
                **self.validated_data,
            )
        except InventoryOperationError as error:
            raise serializers.ValidationError({"detail": str(error)}) from error
        self.instance = movement
        return asset, movement


class AssetMovementSerializer(serializers.ModelSerializer):
    movement_type_display = serializers.CharField(
        source="get_movement_type_display", read_only=True
    )
    asset_tag = serializers.CharField(source="asset.asset_tag", read_only=True)
    from_sector_name = serializers.CharField(source="from_sector.name", read_only=True)
    to_sector_name = serializers.CharField(source="to_sector.name", read_only=True)
    responsible_name = serializers.CharField(source="responsible.name", read_only=True)
    performed_by_username = serializers.CharField(source="performed_by.username", read_only=True)

    class Meta:
        model = AssetMovement
        fields = (
            "id",
            "asset",
            "asset_tag",
            "movement_type",
            "movement_type_display",
            "from_sector",
            "from_sector_name",
            "to_sector",
            "to_sector_name",
            "responsible",
            "responsible_name",
            "loan",
            "performed_by_username",
            "notes",
            "created_at",
        )
        read_only_fields = fields
