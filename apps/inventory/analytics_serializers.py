from rest_framework import serializers


class DashboardSummarySerializer(serializers.Serializer):
    total_assets = serializers.IntegerField()
    total_purchase_value = serializers.DecimalField(max_digits=14, decimal_places=2)
    active_loans = serializers.IntegerField()
    overdue_loans = serializers.IntegerField()
    open_maintenances = serializers.IntegerField()
    maintenance_cost_current_year = serializers.DecimalField(max_digits=14, decimal_places=2)
    warranties_expiring_in_30_days = serializers.IntegerField()


class DistributionItemSerializer(serializers.Serializer):
    key = serializers.IntegerField()
    label = serializers.CharField()
    total = serializers.IntegerField()


class CostTrendItemSerializer(serializers.Serializer):
    month = serializers.DateField()
    total = serializers.DecimalField(max_digits=14, decimal_places=2)


class LatestMovementSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    asset_tag = serializers.CharField()
    asset_name = serializers.CharField()
    movement_type = serializers.CharField()
    movement_type_display = serializers.CharField()
    performed_by = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()


class InventoryDashboardSerializer(serializers.Serializer):
    generated_at = serializers.DateTimeField()
    summary = DashboardSummarySerializer()
    assets_by_status = DistributionItemSerializer(many=True)
    assets_by_category = DistributionItemSerializer(many=True)
    assets_by_sector = DistributionItemSerializer(many=True)
    cost_trend = CostTrendItemSerializer(many=True)
    latest_movements = LatestMovementSerializer(many=True)
