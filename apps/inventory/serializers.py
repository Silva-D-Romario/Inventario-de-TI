from pathlib import Path

from django.urls import reverse
from django.utils import timezone
from rest_framework import serializers

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
    ResponsiblePerson,
    Sector,
    Warranty,
)
from apps.inventory.services import (
    InventoryOperationError,
    create_loan,
    create_maintenance,
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
    qr_code_url = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = (
            "id",
            "public_id",
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
            "qr_code_url",
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
            "public_id",
            "responsible",
            "responsible_name",
            "qr_code_url",
            "created_by_username",
            "created_at",
            "updated_at",
        )

    def get_qr_code_url(self, instance) -> str:
        request = self.context.get("request")
        path = reverse("asset-qr-code", kwargs={"pk": instance.pk})
        return request.build_absolute_uri(path) if request else path

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


class MaintenanceSerializer(serializers.ModelSerializer):
    asset_tag = serializers.CharField(source="asset.asset_tag", read_only=True)
    maintenance_type_display = serializers.CharField(
        source="get_maintenance_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Maintenance
        fields = (
            "id",
            "asset",
            "asset_tag",
            "maintenance_type",
            "maintenance_type_display",
            "status",
            "status_display",
            "description",
            "provider",
            "started_at",
            "completed_at",
            "cost",
            "resolution_notes",
            "is_active",
            "created_by_username",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "status_display",
            "completed_at",
            "cost",
            "resolution_notes",
            "is_active",
            "created_by_username",
            "created_at",
            "updated_at",
        )

    def validate_started_at(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("A manutenção não pode começar no futuro.")
        return value

    def create(self, validated_data):
        validated_data.setdefault("started_at", timezone.localdate())
        validated_data.setdefault("provider", "")
        try:
            return create_maintenance(user=self.context["request"].user, **validated_data)
        except InventoryOperationError as error:
            raise serializers.ValidationError({"detail": str(error)}) from error


class FinishMaintenanceSerializer(serializers.Serializer):
    resolution_notes = serializers.CharField(required=False, allow_blank=True, default="")
    cost = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
        default=0,
    )


class WarrantySerializer(serializers.ModelSerializer):
    asset_tag = serializers.CharField(source="asset.asset_tag", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Warranty
        fields = (
            "id",
            "asset",
            "asset_tag",
            "provider",
            "contract_number",
            "start_date",
            "end_date",
            "coverage_notes",
            "is_active",
            "created_by_username",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "is_active",
            "created_by_username",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "A garantia não pode terminar antes da data de início."}
            )
        return attrs


class AssetCostSerializer(serializers.ModelSerializer):
    asset_tag = serializers.CharField(source="asset.asset_tag", read_only=True)
    cost_type_display = serializers.CharField(source="get_cost_type_display", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = AssetCost
        fields = (
            "id",
            "asset",
            "asset_tag",
            "maintenance",
            "cost_type",
            "cost_type_display",
            "amount",
            "occurred_on",
            "description",
            "created_by_username",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_by_username",
            "created_at",
            "updated_at",
        )

    def validate_occurred_on(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("A data do custo não pode estar no futuro.")
        return value

    def validate(self, attrs):
        asset = attrs.get("asset", getattr(self.instance, "asset", None))
        maintenance = attrs.get("maintenance", getattr(self.instance, "maintenance", None))
        if maintenance and asset and maintenance.asset_id != asset.pk:
            raise serializers.ValidationError(
                {"maintenance": "A manutenção deve pertencer ao ativo informado."}
            )
        return attrs


class AssetAttachmentSerializer(serializers.ModelSerializer):
    asset_tag = serializers.CharField(source="asset.asset_tag", read_only=True)
    file_name = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    uploaded_by_username = serializers.CharField(source="uploaded_by.username", read_only=True)

    class Meta:
        model = AssetAttachment
        fields = (
            "id",
            "asset",
            "asset_tag",
            "maintenance",
            "file",
            "file_name",
            "download_url",
            "description",
            "uploaded_by_username",
            "created_at",
        )
        read_only_fields = (
            "id",
            "file_name",
            "download_url",
            "uploaded_by_username",
            "created_at",
        )
        extra_kwargs = {"file": {"write_only": True}}

    def get_file_name(self, instance) -> str:
        return Path(instance.file.name).name

    def get_download_url(self, instance) -> str:
        request = self.context.get("request")
        path = reverse("asset-attachment-download", kwargs={"pk": instance.pk})
        return request.build_absolute_uri(path) if request else path

    def validate_file(self, uploaded_file):
        suffix = Path(uploaded_file.name).suffix.lower()
        header = uploaded_file.read(16)
        uploaded_file.seek(0)
        valid_content = {
            ".pdf": header.startswith(b"%PDF-"),
            ".png": header.startswith(b"\x89PNG\r\n\x1a\n"),
            ".jpg": header.startswith(b"\xff\xd8\xff"),
            ".jpeg": header.startswith(b"\xff\xd8\xff"),
            ".webp": header.startswith(b"RIFF") and header[8:12] == b"WEBP",
        }
        if not valid_content.get(suffix, False):
            raise serializers.ValidationError(
                "O conteúdo do arquivo não corresponde a um formato permitido."
            )
        return uploaded_file

    def validate(self, attrs):
        asset = attrs["asset"]
        maintenance = attrs.get("maintenance")
        if maintenance and maintenance.asset_id != asset.pk:
            raise serializers.ValidationError(
                {"maintenance": "A manutenção deve pertencer ao ativo informado."}
            )
        return attrs


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
            "maintenance",
            "performed_by_username",
            "notes",
            "created_at",
        )
        read_only_fields = fields


class AuditLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source="get_action_display", read_only=True)
    actor_username = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "actor",
            "actor_username",
            "action",
            "action_display",
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
        read_only_fields = fields
