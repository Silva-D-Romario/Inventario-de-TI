import csv
from io import StringIO

from rest_framework import serializers

from apps.inventory.models import Asset, AssetCost, Maintenance


def _validate_period(attrs, start_field, end_field):
    start = attrs.get(start_field)
    end = attrs.get(end_field)
    if start and end and start > end:
        raise serializers.ValidationError(
            {end_field: "A data final não pode anteceder a data inicial."}
        )
    return attrs


class AssetReportFilterSerializer(serializers.Serializer):
    category = serializers.IntegerField(required=False, min_value=1)
    sector = serializers.IntegerField(required=False, min_value=1)
    status = serializers.IntegerField(required=False, min_value=1)
    acquisition_from = serializers.DateField(required=False)
    acquisition_to = serializers.DateField(required=False)

    def validate(self, attrs):
        return _validate_period(attrs, "acquisition_from", "acquisition_to")


class CostReportFilterSerializer(serializers.Serializer):
    asset = serializers.IntegerField(required=False, min_value=1)
    cost_type = serializers.ChoiceField(required=False, choices=AssetCost.Type.choices)
    occurred_from = serializers.DateField(required=False)
    occurred_to = serializers.DateField(required=False)

    def validate(self, attrs):
        return _validate_period(attrs, "occurred_from", "occurred_to")


class MaintenanceReportFilterSerializer(serializers.Serializer):
    asset = serializers.IntegerField(required=False, min_value=1)
    status = serializers.ChoiceField(required=False, choices=Maintenance.Status.choices)
    maintenance_type = serializers.ChoiceField(required=False, choices=Maintenance.Type.choices)
    started_from = serializers.DateField(required=False)
    started_to = serializers.DateField(required=False)

    def validate(self, attrs):
        return _validate_period(attrs, "started_from", "started_to")


def filter_assets(filters):
    queryset = Asset.objects.select_related("category", "sector", "status", "responsible")
    if category := filters.get("category"):
        queryset = queryset.filter(category_id=category)
    if sector := filters.get("sector"):
        queryset = queryset.filter(sector_id=sector)
    if status := filters.get("status"):
        queryset = queryset.filter(status_id=status)
    if start := filters.get("acquisition_from"):
        queryset = queryset.filter(acquisition_date__gte=start)
    if end := filters.get("acquisition_to"):
        queryset = queryset.filter(acquisition_date__lte=end)
    return queryset.order_by("asset_tag")


def filter_costs(filters):
    queryset = AssetCost.objects.select_related("asset", "maintenance")
    if asset := filters.get("asset"):
        queryset = queryset.filter(asset_id=asset)
    if cost_type := filters.get("cost_type"):
        queryset = queryset.filter(cost_type=cost_type)
    if start := filters.get("occurred_from"):
        queryset = queryset.filter(occurred_on__gte=start)
    if end := filters.get("occurred_to"):
        queryset = queryset.filter(occurred_on__lte=end)
    return queryset.order_by("-occurred_on", "asset__asset_tag")


def filter_maintenances(filters):
    queryset = Maintenance.objects.select_related("asset")
    if asset := filters.get("asset"):
        queryset = queryset.filter(asset_id=asset)
    if status := filters.get("status"):
        queryset = queryset.filter(status=status)
    if maintenance_type := filters.get("maintenance_type"):
        queryset = queryset.filter(maintenance_type=maintenance_type)
    if start := filters.get("started_from"):
        queryset = queryset.filter(started_at__gte=start)
    if end := filters.get("started_to"):
        queryset = queryset.filter(started_at__lte=end)
    return queryset.order_by("-started_at", "asset__asset_tag")


def safe_csv_cell(value):
    if value is None:
        return ""
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


def render_csv(headers, rows):
    output = StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";", lineterminator="\n")
    writer.writerow(headers)
    writer.writerows([safe_csv_cell(value) for value in row] for row in rows)
    return output.getvalue()
