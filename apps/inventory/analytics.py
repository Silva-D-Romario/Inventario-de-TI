from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, F, Sum
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

from apps.inventory.models import (
    Asset,
    AssetCost,
    AssetMovement,
    Loan,
    Maintenance,
    Warranty,
)

MONEY_FIELD = DecimalField(max_digits=14, decimal_places=2)


def _distribution(queryset, field, label_field):
    return list(
        queryset.values(key=F(field), label=F(label_field))
        .annotate(total=Count("id"))
        .order_by("label")
    )


def build_inventory_dashboard():
    today = timezone.localdate()
    cost_period_start = today.replace(day=1) - timedelta(days=365)

    purchase_value = Asset.objects.aggregate(
        total=Coalesce(Sum("purchase_value"), Decimal("0.00"), output_field=MONEY_FIELD)
    )["total"]
    maintenance_cost_year = Maintenance.objects.filter(
        status=Maintenance.Status.COMPLETED,
        completed_at__year=today.year,
    ).aggregate(total=Coalesce(Sum("cost"), Decimal("0.00"), output_field=MONEY_FIELD))["total"]

    cost_trend = list(
        AssetCost.objects.filter(occurred_on__gte=cost_period_start)
        .annotate(month=TruncMonth("occurred_on"))
        .values("month")
        .annotate(total=Coalesce(Sum("amount"), Decimal("0.00"), output_field=MONEY_FIELD))
        .order_by("month")
    )
    latest_movements = [
        {
            "id": movement.id,
            "asset_tag": movement.asset.asset_tag,
            "asset_name": movement.asset.name,
            "movement_type": movement.movement_type,
            "movement_type_display": movement.get_movement_type_display(),
            "performed_by": movement.performed_by.username if movement.performed_by else None,
            "created_at": movement.created_at,
        }
        for movement in AssetMovement.objects.select_related("asset", "performed_by")[:5]
    ]

    assets = Asset.objects.all()
    return {
        "generated_at": timezone.now(),
        "summary": {
            "total_assets": assets.count(),
            "total_purchase_value": purchase_value,
            "active_loans": Loan.objects.filter(returned_at__isnull=True).count(),
            "overdue_loans": Loan.objects.filter(
                returned_at__isnull=True,
                expected_return_date__lt=today,
            ).count(),
            "open_maintenances": Maintenance.objects.filter(
                status=Maintenance.Status.IN_PROGRESS
            ).count(),
            "maintenance_cost_current_year": maintenance_cost_year,
            "warranties_expiring_in_30_days": Warranty.objects.filter(
                end_date__gte=today,
                end_date__lte=today + timedelta(days=30),
            ).count(),
        },
        "assets_by_status": _distribution(assets, "status_id", "status__name"),
        "assets_by_category": _distribution(assets, "category_id", "category__name"),
        "assets_by_sector": _distribution(assets, "sector_id", "sector__name"),
        "cost_trend": cost_trend,
        "latest_movements": latest_movements,
    }
