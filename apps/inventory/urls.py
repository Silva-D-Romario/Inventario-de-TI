from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.inventory.views import (
    AssetMovementViewSet,
    AssetStatusViewSet,
    AssetTransferView,
    AssetViewSet,
    CategoryViewSet,
    LoanViewSet,
    ResponsiblePersonViewSet,
    SectorViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("sectors", SectorViewSet, basename="sector")
router.register("statuses", AssetStatusViewSet, basename="asset-status")
router.register("assets", AssetViewSet, basename="asset")
router.register("responsible-people", ResponsiblePersonViewSet, basename="responsible-person")
router.register("loans", LoanViewSet, basename="loan")
router.register("movements", AssetMovementViewSet, basename="asset-movement")

urlpatterns = [
    path("assets/<int:pk>/transfer/", AssetTransferView.as_view(), name="asset-transfer"),
    *router.urls,
]
