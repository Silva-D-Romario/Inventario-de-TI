from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.inventory.views import (
    AssetAttachmentViewSet,
    AssetCostViewSet,
    AssetCsvReportView,
    AssetMovementViewSet,
    AssetStatusViewSet,
    AssetTransferView,
    AssetViewSet,
    AuditLogViewSet,
    CategoryViewSet,
    CostCsvReportView,
    InventoryDashboardView,
    LoanViewSet,
    MaintenanceCsvReportView,
    MaintenanceViewSet,
    ResponsiblePersonViewSet,
    SectorViewSet,
    WarrantyViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("sectors", SectorViewSet, basename="sector")
router.register("statuses", AssetStatusViewSet, basename="asset-status")
router.register("assets", AssetViewSet, basename="asset")
router.register("responsible-people", ResponsiblePersonViewSet, basename="responsible-person")
router.register("loans", LoanViewSet, basename="loan")
router.register("maintenances", MaintenanceViewSet, basename="maintenance")
router.register("warranties", WarrantyViewSet, basename="warranty")
router.register("costs", AssetCostViewSet, basename="asset-cost")
router.register("attachments", AssetAttachmentViewSet, basename="asset-attachment")
router.register("movements", AssetMovementViewSet, basename="asset-movement")
router.register("audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("dashboard/", InventoryDashboardView.as_view(), name="inventory-dashboard"),
    path("reports/assets.csv", AssetCsvReportView.as_view(), name="asset-csv-report"),
    path("reports/costs.csv", CostCsvReportView.as_view(), name="cost-csv-report"),
    path(
        "reports/maintenances.csv",
        MaintenanceCsvReportView.as_view(),
        name="maintenance-csv-report",
    ),
    path("assets/<int:pk>/transfer/", AssetTransferView.as_view(), name="asset-transfer"),
    *router.urls,
]
