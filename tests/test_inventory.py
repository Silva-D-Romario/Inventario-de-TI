from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.inventory.models import Asset, AssetStatus, Category, Sector


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username="solicitante",
        email="solicitante@example.com",
        password="SenhaSegura@2026",
    )


@pytest.fixture
def technician(db):
    return User.objects.create_user(
        username="tecnico",
        email="tecnico@example.com",
        password="SenhaSegura@2026",
        role=User.Role.TECHNICIAN,
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="administrador",
        email="administrador@example.com",
        password="SenhaSegura@2026",
        role=User.Role.ADMIN,
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name="Notebook")


@pytest.fixture
def sector(db):
    return Sector.objects.create(name="Suporte", location="Bloco A")


@pytest.fixture
def asset_status(db):
    return AssetStatus.objects.get(code="available")


@pytest.fixture
def asset(category, sector, asset_status, technician):
    return Asset.objects.create(
        asset_tag="PAT-001",
        name="Notebook Dell",
        category=category,
        sector=sector,
        status=asset_status,
        serial_number="SN-001",
        manufacturer="Dell",
        model="Latitude",
        created_by=technician,
    )


def authenticate(client, user):
    client.force_authenticate(user=user)


def asset_payload(category, sector, asset_status, asset_tag="PAT-100"):
    return {
        "asset_tag": asset_tag,
        "name": "Notebook de teste",
        "category": category.pk,
        "sector": sector.pk,
        "status": asset_status.pk,
        "serial_number": "",
        "manufacturer": "Lenovo",
        "model": "ThinkPad",
        "purchase_value": "3500.00",
    }


@pytest.mark.django_db
def test_default_asset_statuses_are_created():
    assert set(AssetStatus.objects.values_list("code", flat=True)) == {
        "available",
        "in-use",
        "maintenance",
        "retired",
    }


@pytest.mark.django_db
def test_inventory_requires_authentication(api_client):
    response = api_client.get(reverse("asset-list"))

    assert response.status_code == 401


@pytest.mark.django_db
def test_regular_user_can_read_asset_with_reference_names(api_client, regular_user, asset):
    authenticate(api_client, regular_user)

    response = api_client.get(reverse("asset-detail", kwargs={"pk": asset.pk}))

    assert response.status_code == 200
    assert response.data["category_name"] == "Notebook"
    assert response.data["sector_name"] == "Suporte"
    assert response.data["status_name"] == "Disponível"
    assert response.data["created_by_username"] == "tecnico"


@pytest.mark.django_db
def test_regular_user_cannot_create_asset(api_client, regular_user, category, sector, asset_status):
    authenticate(api_client, regular_user)

    response = api_client.post(
        reverse("asset-list"),
        asset_payload(category, sector, asset_status),
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_technician_can_create_and_update_asset(
    api_client, technician, category, sector, asset_status
):
    authenticate(api_client, technician)
    create_response = api_client.post(
        reverse("asset-list"),
        asset_payload(category, sector, asset_status, asset_tag=" pat-200 "),
        format="json",
    )

    assert create_response.status_code == 201
    created = Asset.objects.get(pk=create_response.data["id"])
    assert created.asset_tag == "PAT-200"
    assert created.created_by == technician
    assert created.serial_number is None

    update_response = api_client.patch(
        reverse("asset-detail", kwargs={"pk": created.pk}),
        {"name": "Notebook atualizado"},
        format="json",
    )

    assert update_response.status_code == 200
    created.refresh_from_db()
    assert created.name == "Notebook atualizado"


@pytest.mark.django_db
def test_technician_cannot_delete_asset(api_client, technician, asset):
    authenticate(api_client, technician)

    response = api_client.delete(reverse("asset-detail", kwargs={"pk": asset.pk}))

    assert response.status_code == 403
    assert Asset.objects.filter(pk=asset.pk).exists()


@pytest.mark.django_db
def test_admin_can_create_update_and_delete_category(api_client, admin_user):
    authenticate(api_client, admin_user)
    create_response = api_client.post(
        reverse("category-list"),
        {"name": "Impressora", "description": "Equipamentos de impressão"},
        format="json",
    )
    category_id = create_response.data["id"]

    assert create_response.status_code == 201
    update_response = api_client.patch(
        reverse("category-detail", kwargs={"pk": category_id}),
        {"description": "Impressoras e multifuncionais"},
        format="json",
    )
    assert update_response.status_code == 200

    delete_response = api_client.delete(reverse("category-detail", kwargs={"pk": category_id}))
    assert delete_response.status_code == 204


@pytest.mark.django_db
def test_technician_cannot_change_reference_data(api_client, technician):
    authenticate(api_client, technician)

    response = api_client.post(
        reverse("sector-list"),
        {"name": "Financeiro"},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_category_name_is_unique_ignoring_case(api_client, admin_user, category):
    authenticate(api_client, admin_user)

    response = api_client.post(
        reverse("category-list"),
        {"name": "notebook"},
        format="json",
    )

    assert response.status_code == 400
    assert "name" in response.data


@pytest.mark.django_db
def test_reference_in_use_cannot_be_deleted(api_client, admin_user, category, asset):
    authenticate(api_client, admin_user)

    response = api_client.delete(reverse("category-detail", kwargs={"pk": category.pk}))

    assert response.status_code == 409
    assert Category.objects.filter(pk=category.pk).exists()


@pytest.mark.django_db
def test_assets_can_be_filtered_and_searched(
    api_client, regular_user, asset, category, sector, asset_status
):
    Asset.objects.create(
        asset_tag="PAT-002",
        name="Monitor LG",
        category=category,
        sector=sector,
        status=asset_status,
    )
    authenticate(api_client, regular_user)

    response = api_client.get(reverse("asset-list"), {"search": "Dell"})

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["asset_tag"] == "PAT-001"


@pytest.mark.django_db
def test_multiple_assets_can_have_empty_serial_number(
    api_client, technician, category, sector, asset_status
):
    authenticate(api_client, technician)

    first = api_client.post(
        reverse("asset-list"),
        asset_payload(category, sector, asset_status, "PAT-300"),
        format="json",
    )
    second = api_client.post(
        reverse("asset-list"),
        asset_payload(category, sector, asset_status, "PAT-301"),
        format="json",
    )

    assert first.status_code == 201
    assert second.status_code == 201


@pytest.mark.django_db
def test_future_acquisition_date_and_negative_value_are_rejected(
    api_client, technician, category, sector, asset_status
):
    authenticate(api_client, technician)
    payload = asset_payload(category, sector, asset_status)
    payload["acquisition_date"] = str(timezone.localdate() + timedelta(days=1))
    payload["purchase_value"] = "-1.00"

    response = api_client.post(reverse("asset-list"), payload, format="json")

    assert response.status_code == 400
    assert "acquisition_date" in response.data
    assert "purchase_value" in response.data


@pytest.mark.django_db
def test_admin_can_delete_asset(api_client, admin_user, asset):
    authenticate(api_client, admin_user)

    response = api_client.delete(reverse("asset-detail", kwargs={"pk": asset.pk}))

    assert response.status_code == 204
    assert not Asset.objects.filter(pk=asset.pk).exists()


@pytest.mark.django_db
def test_status_rejects_invalid_color(api_client, admin_user):
    authenticate(api_client, admin_user)

    response = api_client.post(
        reverse("asset-status-list"),
        {"code": "reserved", "name": "Reservado", "color": "verde"},
        format="json",
    )

    assert response.status_code == 400
    assert "color" in response.data
