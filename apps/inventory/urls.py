from rest_framework.routers import DefaultRouter

from apps.inventory.views import (
    AssetStatusViewSet,
    AssetViewSet,
    CategoryViewSet,
    SectorViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("sectors", SectorViewSet, basename="sector")
router.register("statuses", AssetStatusViewSet, basename="asset-status")
router.register("assets", AssetViewSet, basename="asset")

urlpatterns = router.urls
