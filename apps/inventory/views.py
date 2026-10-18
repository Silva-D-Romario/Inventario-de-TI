from django.db.models import ProtectedError
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.inventory.models import (
    Asset,
    AssetMovement,
    AssetStatus,
    Category,
    Loan,
    ResponsiblePerson,
    Sector,
)
from apps.inventory.permissions import (
    AssetPermission,
    MasterDataPermission,
    OperationalPermission,
)
from apps.inventory.serializers import (
    AssetMovementSerializer,
    AssetSerializer,
    AssetStatusSerializer,
    CategorySerializer,
    LoanSerializer,
    ResponsiblePersonSerializer,
    ReturnLoanSerializer,
    SectorSerializer,
    TransferAssetSerializer,
)
from apps.inventory.services import InventoryOperationError, return_loan


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


class ReferenceViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
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
class AssetViewSet(viewsets.ModelViewSet):
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

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


@extend_schema_view(list=extend_schema(tags=["Responsáveis"]))
class ResponsiblePersonViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
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
        return Response(LoanSerializer(returned_loan).data)


@extend_schema_view(list=extend_schema(tags=["Movimentações"]))
class AssetMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AssetMovement.objects.select_related(
        "asset",
        "from_sector",
        "to_sector",
        "responsible",
        "loan",
        "performed_by",
    )
    serializer_class = AssetMovementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ("asset", "movement_type", "from_sector", "to_sector", "responsible")
    search_fields = ("asset__asset_tag", "asset__name", "responsible__name")
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
        return Response(AssetSerializer(updated_asset).data)
