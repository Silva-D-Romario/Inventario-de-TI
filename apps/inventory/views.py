from django.db.models import ProtectedError
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.response import Response

from apps.inventory.models import Asset, AssetStatus, Category, Sector
from apps.inventory.permissions import AssetPermission, MasterDataPermission
from apps.inventory.serializers import (
    AssetSerializer,
    AssetStatusSerializer,
    CategorySerializer,
    SectorSerializer,
)


class ProtectedDestroyMixin:
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
        except ProtectedError:
            return Response(
                {"detail": "Este cadastro está vinculado a um ou mais ativos."},
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
    queryset = Asset.objects.select_related("category", "sector", "status", "created_by")
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
