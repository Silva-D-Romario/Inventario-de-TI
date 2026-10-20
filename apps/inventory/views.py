from decimal import Decimal
from io import BytesIO
from pathlib import Path

import qrcode
from django.db.models import ProtectedError
from django.http import FileResponse, HttpResponse
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view
from qrcode.constants import ERROR_CORRECT_M
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsAdministrator
from apps.inventory.analytics import build_inventory_dashboard
from apps.inventory.analytics_serializers import InventoryDashboardSerializer
from apps.inventory.audit import AuditTrailMixin, record_audit
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
from apps.inventory.permissions import (
    AssetPermission,
    MasterDataPermission,
    OperationalPermission,
)
from apps.inventory.serializers import (
    AssetAttachmentSerializer,
    AssetCostSerializer,
    AssetMovementSerializer,
    AssetSerializer,
    AssetStatusSerializer,
    AuditLogSerializer,
    CategorySerializer,
    FinishMaintenanceSerializer,
    LoanSerializer,
    MaintenanceSerializer,
    ResponsiblePersonSerializer,
    ReturnLoanSerializer,
    SectorSerializer,
    TransferAssetSerializer,
    WarrantySerializer,
)
from apps.inventory.services import (
    InventoryOperationError,
    finish_maintenance,
    return_loan,
)


class ProtectedDestroyMixin:
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
        except ProtectedError:
            return Response(
                {"detail": "Este cadastro está vinculado a registros do inventário."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReferenceViewSet(AuditTrailMixin, ProtectedDestroyMixin, viewsets.ModelViewSet):
    permission_classes = [MasterDataPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ("is_active",)
    search_fields = ("name",)
    ordering_fields = ("name", "created_at", "updated_at")
    ordering = ("name",)


@extend_schema_view(list=extend_schema(tags=["Categorias"]))
class CategoryViewSet(ReferenceViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


@extend_schema_view(list=extend_schema(tags=["Setores"]))
class SectorViewSet(ReferenceViewSet):
    queryset = Sector.objects.all()
    serializer_class = SectorSerializer
    search_fields = ("name", "location")


@extend_schema_view(list=extend_schema(tags=["Status dos ativos"]))
class AssetStatusViewSet(ReferenceViewSet):
    queryset = AssetStatus.objects.all()
    serializer_class = AssetStatusSerializer
    search_fields = ("name", "code")


@extend_schema_view(list=extend_schema(tags=["Ativos"]))
class AssetViewSet(AuditTrailMixin, ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = Asset.objects.select_related(
        "category", "sector", "status", "responsible", "created_by"
    )
    serializer_class = AssetSerializer
    permission_classes = [AssetPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        "category": ["exact"],
        "sector": ["exact"],
        "status": ["exact"],
        "acquisition_date": ["exact", "gte", "lte"],
    }
    search_fields = ("asset_tag", "name", "serial_number", "manufacturer", "model")
    ordering_fields = ("asset_tag", "name", "acquisition_date", "purchase_value", "updated_at")
    ordering = ("asset_tag",)

    def get_create_save_kwargs(self):
        return {"created_by": self.request.user}

    @extend_schema(responses={(200, "image/png"): OpenApiTypes.BINARY})
    @action(detail=True, methods=("get",), url_path="qr-code")
    def qr_code(self, request, pk=None):
        asset = self.get_object()
        scan_url = request.build_absolute_uri(
            reverse("asset-scan", kwargs={"public_id": asset.public_id})
        )
        qr = qrcode.QRCode(
            error_correction=ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(scan_url)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white")
        output = BytesIO()
        image.save(output, format="PNG")
        response = HttpResponse(output.getvalue(), content_type="image/png")
        response["Content-Disposition"] = f'inline; filename="ativo-{asset.asset_tag}-qrcode.png"'
        response["Cache-Control"] = "private, max-age=3600"
        return response

    @action(
        detail=False,
        methods=("get",),
        url_path=r"scan/(?P<public_id>[0-9a-fA-F-]{36})",
    )
    def scan(self, request, public_id=None):
        asset = get_object_or_404(self.get_queryset(), public_id=public_id)
        record_audit(
            request=request,
            action=AuditLog.Action.SCAN,
            instance=asset,
            changes={"event": "QR_SCAN"},
        )
        return Response(self.get_serializer(asset).data)


@extend_schema_view(list=extend_schema(tags=["Responsáveis"]))
class ResponsiblePersonViewSet(AuditTrailMixin, ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = ResponsiblePerson.objects.select_related("sector")
    serializer_class = ResponsiblePersonSerializer
    permission_classes = [OperationalPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ("sector", "is_active")
    search_fields = ("name", "email", "employee_id")
    ordering_fields = ("name", "created_at", "updated_at")
    ordering = ("name",)


@extend_schema_view(list=extend_schema(tags=["Empréstimos"]))
class LoanViewSet(
    AuditTrailMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Loan.objects.select_related("asset", "borrower", "created_by")
    serializer_class = LoanSerializer
    permission_classes = [OperationalPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        "asset": ["exact"],
        "borrower": ["exact"],
        "returned_at": ["isnull", "exact"],
        "expected_return_date": ["exact", "gte", "lte"],
    }
    search_fields = ("asset__asset_tag", "asset__name", "borrower__name")
    ordering_fields = ("loaned_at", "expected_return_date", "returned_at", "created_at")
    ordering = ("-loaned_at", "-created_at")

    @action(detail=True, methods=("post",), url_path="return")
    def return_asset(self, request, pk=None):
        loan = self.get_object()
        serializer = ReturnLoanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            returned_loan = return_loan(
                loan=loan,
                notes=serializer.validated_data["notes"],
                user=request.user,
            )
        except InventoryOperationError as error:
            raise ValidationError({"detail": str(error)}) from error
        record_audit(
            request=request,
            action=AuditLog.Action.ACTION,
            instance=returned_loan,
            changes={
                "event": "RETURN",
                "asset": returned_loan.asset_id,
                "notes": serializer.validated_data["notes"],
            },
        )
        return Response(LoanSerializer(returned_loan).data)


@extend_schema_view(list=extend_schema(tags=["Manutenções"]))
class MaintenanceViewSet(
    AuditTrailMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Maintenance.objects.select_related("asset", "created_by")
    serializer_class = MaintenanceSerializer
    permission_classes = [OperationalPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        "asset": ["exact"],
        "maintenance_type": ["exact"],
        "status": ["exact"],
        "started_at": ["exact", "gte", "lte"],
        "completed_at": ["exact", "gte", "lte", "isnull"],
    }
    search_fields = ("asset__asset_tag", "asset__name", "description", "provider")
    ordering_fields = ("started_at", "completed_at", "cost", "created_at")
    ordering = ("-started_at", "-created_at")

    def _finish(self, request, maintenance, final_status):
        serializer = FinishMaintenanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cost = serializer.validated_data["cost"]
        if final_status == Maintenance.Status.CANCELLED:
            cost = Decimal("0.00")
        try:
            finished = finish_maintenance(
                maintenance=maintenance,
                final_status=final_status,
                resolution_notes=serializer.validated_data["resolution_notes"],
                cost=cost,
                user=request.user,
            )
        except InventoryOperationError as error:
            raise ValidationError({"detail": str(error)}) from error
        record_audit(
            request=request,
            action=AuditLog.Action.ACTION,
            instance=finished,
            changes={
                "event": final_status,
                "cost": cost,
                "resolution_notes": serializer.validated_data["resolution_notes"],
            },
        )
        return Response(self.get_serializer(finished).data)

    @action(detail=True, methods=("post",))
    def complete(self, request, pk=None):
        return self._finish(request, self.get_object(), Maintenance.Status.COMPLETED)

    @action(detail=True, methods=("post",))
    def cancel(self, request, pk=None):
        return self._finish(request, self.get_object(), Maintenance.Status.CANCELLED)


@extend_schema_view(list=extend_schema(tags=["Garantias"]))
class WarrantyViewSet(AuditTrailMixin, ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = Warranty.objects.select_related("asset", "created_by")
    serializer_class = WarrantySerializer
    permission_classes = [OperationalPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        "asset": ["exact"],
        "start_date": ["exact", "gte", "lte"],
        "end_date": ["exact", "gte", "lte"],
    }
    search_fields = ("asset__asset_tag", "asset__name", "provider", "contract_number")
    ordering_fields = ("start_date", "end_date", "created_at", "updated_at")
    ordering = ("-end_date",)

    def get_create_save_kwargs(self):
        return {"created_by": self.request.user}


@extend_schema_view(list=extend_schema(tags=["Custos"]))
class AssetCostViewSet(AuditTrailMixin, ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = AssetCost.objects.select_related("asset", "maintenance", "created_by")
    serializer_class = AssetCostSerializer
    permission_classes = [OperationalPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        "asset": ["exact"],
        "maintenance": ["exact", "isnull"],
        "cost_type": ["exact"],
        "occurred_on": ["exact", "gte", "lte"],
    }
    search_fields = ("asset__asset_tag", "asset__name", "description")
    ordering_fields = ("occurred_on", "amount", "created_at", "updated_at")
    ordering = ("-occurred_on", "-created_at")

    def get_create_save_kwargs(self):
        return {"created_by": self.request.user}


@extend_schema_view(list=extend_schema(tags=["Anexos"]))
class AssetAttachmentViewSet(
    AuditTrailMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = AssetAttachment.objects.select_related("asset", "maintenance", "uploaded_by")
    serializer_class = AssetAttachmentSerializer
    permission_classes = [OperationalPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {"asset": ["exact"], "maintenance": ["exact", "isnull"]}
    search_fields = ("asset__asset_tag", "asset__name", "description")
    ordering_fields = ("created_at",)
    ordering = ("-created_at",)

    def get_create_save_kwargs(self):
        return {"uploaded_by": self.request.user}

    @action(detail=True, methods=("get",))
    def download(self, request, pk=None):
        attachment = self.get_object()
        return FileResponse(
            attachment.file.open("rb"),
            as_attachment=True,
            filename=Path(attachment.file.name).name,
        )


@extend_schema_view(list=extend_schema(tags=["Movimentações"]))
class AssetMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AssetMovement.objects.select_related(
        "asset",
        "from_sector",
        "to_sector",
        "responsible",
        "loan",
        "maintenance",
        "performed_by",
    )
    serializer_class = AssetMovementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ("asset", "movement_type", "from_sector", "to_sector", "responsible")
    search_fields = ("asset__asset_tag", "asset__name", "responsible__name")
    ordering_fields = ("created_at",)
    ordering = ("-created_at",)


@extend_schema_view(list=extend_schema(tags=["Auditoria"]))
class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("actor")
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdministrator]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        "actor": ["exact"],
        "action": ["exact"],
        "resource_type": ["exact"],
        "object_id": ["exact"],
        "created_at": ["date", "gte", "lte"],
    }
    search_fields = ("actor__username", "object_repr", "path")
    ordering_fields = ("created_at",)
    ordering = ("-created_at",)


class AssetTransferView(GenericAPIView):
    serializer_class = TransferAssetSerializer
    permission_classes = [AssetPermission]

    def post(self, request, pk):
        asset = get_object_or_404(Asset.objects.select_related("sector", "status"), pk=pk)
        serializer = self.get_serializer(
            data=request.data, context={"request": request, "asset": asset}
        )
        serializer.is_valid(raise_exception=True)
        updated_asset, _movement = serializer.save()
        record_audit(
            request=request,
            action=AuditLog.Action.ACTION,
            instance=updated_asset,
            changes={
                "event": "TRANSFER",
                "to_sector": updated_asset.sector_id,
                "responsible": updated_asset.responsible_id,
                "notes": serializer.validated_data["notes"],
            },
        )
        return Response(AssetSerializer(updated_asset).data)


class InventoryDashboardView(GenericAPIView):
    serializer_class = InventoryDashboardSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Dashboard"], responses=InventoryDashboardSerializer)
    def get(self, request):
        serializer = self.get_serializer(build_inventory_dashboard())
        return Response(serializer.data)
