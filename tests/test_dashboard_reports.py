import csv
from datetime import timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.inventory.models import (
    Asset,
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


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username="usuario-dashboard",
        email="usuario-dashboard@example.com",
        password="SenhaSegura@2026",
    )


@pytest.fixture
def technician(db):
    return User.objects.create_user(
        username="tecnico-dashboard",
        email="tecnico-dashboard@example.com",
        password="SenhaSegura@2026",
        role=User.Role.TECHNICIAN,
    )


@pytest.fixture
def dashboard_data(db, technician):
    today = timezone.localdate()
    notebooks = Category.objects.create(name="Notebooks")
    printers = Category.objects.create(name="Impressoras")
    support = Sector.objects.create(name="Suporte")
    finance = Sector.objects.create(name="Financeiro")
    available = AssetStatus.objects.get(code="available")
    maintenance_status = AssetStatus.objects.get(code="maintenance")
    first_asset = Asset.objects.create(
        asset_tag="PAT-DASH-001",
        name="=Notebook Dell",
        category=notebooks,
        sector=support,
        status=available,
        acquisition_date=today - timedelta(days=30),
        purchase_value=Decimal("3500.00"),
        created_by=technician,
    )
    second_asset = Asset.objects.create(
        asset_tag="PAT-DASH-002",
        name="Impressora HP",
        category=printers,
        sector=finance,
        status=maintenance_status,
        acquisition_date=today - timedelta(days=10),
        purchase_value=Decimal("1500.00"),
        created_by=technician,
    )
    borrower = ResponsiblePerson.objects.create(
        name="Maria Silva",
        email="maria.dashboard@example.com",
        sector=support,
    )
    Loan.objects.create(
        asset=first_asset,
        borrower=borrower,
        loaned_at=today - timedelta(days=10),
        expected_return_date=today - timedelta(days=1),
        created_by=technician,
    )
    completed_maintenance = Maintenance.objects.create(
        asset=first_asset,
        maintenance_type=Maintenance.Type.PREVENTIVE,
        status=Maintenance.Status.COMPLETED,
        description="Limpeza",
        started_at=today - timedelta(days=5),
        completed_at=today - timedelta(days=4),
        cost=Decimal("150.00"),
        created_by=technician,
    )
    open_maintenance = Maintenance.objects.create(
        asset=second_asset,
        maintenance_type=Maintenance.Type.CORRECTIVE,
        description="Troca de fusor",
        started_at=today,
        created_by=technician,
    )
    Warranty.objects.create(
        asset=second_asset,
        provider="HP",
        start_date=today - timedelta(days=300),
        end_date=today + timedelta(days=15),
        created_by=technician,
    )
    first_cost = AssetCost.objects.create(
        asset=first_asset,
        maintenance=completed_maintenance,
        cost_type=AssetCost.Type.MAINTENANCE,
        amount=Decimal("150.00"),
        occurred_on=today - timedelta(days=4),
        description="Limpeza preventiva",
        created_by=technician,
    )
    AssetCost.objects.create(
        asset=second_asset,
        cost_type=AssetCost.Type.LICENSE,
        amount=Decimal("50.00"),
        occurred_on=today,
        description="Licença",
        created_by=technician,
    )
    movement = AssetMovement.objects.create(
        asset=second_asset,
        movement_type=AssetMovement.Type.MAINTENANCE_START,
        maintenance=open_maintenance,
        performed_by=technician,
    )
    return {
        "today": today,
        "notebooks": notebooks,
        "support": support,
        "available": available,
        "first_asset": first_asset,
        "second_asset": second_asset,
        "first_cost": first_cost,
        "completed_maintenance": completed_maintenance,
        "open_maintenance": open_maintenance,
        "movement": movement,
    }


def authenticate(client, user):
    client.force_authenticate(user=user)


def csv_rows(response):
    content = response.content.decode("utf-8-sig")
    return list(csv.reader(StringIO(content), delimiter=";"))


@pytest.mark.django_db
def test_dashboard_requires_authentication(api_client):
    response = api_client.get(reverse("inventory-dashboard"))

    assert response.status_code == 401


@pytest.mark.django_db
def test_dashboard_returns_kpis_distributions_and_charts(api_client, regular_user, dashboard_data):
    authenticate(api_client, regular_user)

    response = api_client.get(reverse("inventory-dashboard"))

    assert response.status_code == 200
    assert response.data["summary"] == {
        "total_assets": 2,
        "total_purchase_value": "5000.00",
        "active_loans": 1,
        "overdue_loans": 1,
        "open_maintenances": 1,
        "maintenance_cost_current_year": "150.00",
        "warranties_expiring_in_30_days": 1,
    }
    assert {item["label"]: item["total"] for item in response.data["assets_by_category"]} == {
        "Impressoras": 1,
        "Notebooks": 1,
    }
    assert sum(item["total"] for item in response.data["assets_by_status"]) == 2
    assert sum(item["total"] for item in response.data["assets_by_sector"]) == 2
    assert sum(Decimal(item["total"]) for item in response.data["cost_trend"]) == Decimal("200.00")
    assert response.data["latest_movements"][0]["id"] == dashboard_data["movement"].id


@pytest.mark.django_db
@pytest.mark.parametrize(
    "route_name",
    ("asset-csv-report", "cost-csv-report", "maintenance-csv-report"),
)
def test_csv_reports_require_technician_or_admin(
    route_name, api_client, regular_user, dashboard_data
):
    authenticate(api_client, regular_user)

    response = api_client.get(reverse(route_name))

    assert response.status_code == 403


@pytest.mark.django_db
def test_asset_report_filters_rows_escapes_formulas_and_audits(
    api_client, technician, dashboard_data
):
    authenticate(api_client, technician)

    response = api_client.get(
        reverse("asset-csv-report"),
        {
            "category": dashboard_data["notebooks"].pk,
            "sector": dashboard_data["support"].pk,
            "status": dashboard_data["available"].pk,
            "acquisition_from": dashboard_data["today"] - timedelta(days=40),
            "acquisition_to": dashboard_data["today"],
        },
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv; charset=utf-8"
    assert 'filename="ativos-' in response["Content-Disposition"]
    rows = csv_rows(response)
    assert len(rows) == 2
    assert rows[1][0] == "PAT-DASH-001"
    assert rows[1][1] == "'=Notebook Dell"
    log = AuditLog.objects.get(resource_type="inventory.report", object_id="ativos")
    assert log.actor == technician
    assert log.changes["event"] == "REPORT_EXPORT"
    assert log.changes["row_count"] == 1


@pytest.mark.django_db
def test_cost_report_filters_by_asset_type_and_period(api_client, technician, dashboard_data):
    authenticate(api_client, technician)

    response = api_client.get(
        reverse("cost-csv-report"),
        {
            "asset": dashboard_data["first_asset"].pk,
            "cost_type": AssetCost.Type.MAINTENANCE,
            "occurred_from": dashboard_data["today"] - timedelta(days=10),
            "occurred_to": dashboard_data["today"],
        },
    )

    rows = csv_rows(response)
    assert response.status_code == 200
    assert len(rows) == 2
    assert rows[1][1:5] == ["PAT-DASH-001", "'=Notebook Dell", "Manutenção", "150.00"]
    assert AuditLog.objects.get(object_id="custos").changes["row_count"] == 1


@pytest.mark.django_db
def test_maintenance_report_filters_status_type_and_period(api_client, technician, dashboard_data):
    authenticate(api_client, technician)

    response = api_client.get(
        reverse("maintenance-csv-report"),
        {
            "asset": dashboard_data["first_asset"].pk,
            "status": Maintenance.Status.COMPLETED,
            "maintenance_type": Maintenance.Type.PREVENTIVE,
            "started_from": dashboard_data["today"] - timedelta(days=10),
            "started_to": dashboard_data["today"],
        },
    )

    rows = csv_rows(response)
    assert response.status_code == 200
    assert len(rows) == 2
    assert rows[1][0:4] == [
        "PAT-DASH-001",
        "'=Notebook Dell",
        "Preventiva",
        "Concluída",
    ]
    assert AuditLog.objects.get(object_id="manutencoes").changes["row_count"] == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("route_name", "start_field", "end_field"),
    (
        ("asset-csv-report", "acquisition_from", "acquisition_to"),
        ("cost-csv-report", "occurred_from", "occurred_to"),
        ("maintenance-csv-report", "started_from", "started_to"),
    ),
)
def test_reports_reject_inverted_date_ranges(
    route_name, start_field, end_field, api_client, technician
):
    authenticate(api_client, technician)

    response = api_client.get(
        reverse(route_name),
        {start_field: "2026-10-20", end_field: "2026-10-01"},
    )

    assert response.status_code == 400
    assert end_field in response.data
    assert not AuditLog.objects.exists()
