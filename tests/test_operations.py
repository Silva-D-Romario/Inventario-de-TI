from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.inventory.models import (
    Asset,
    AssetMovement,
    AssetStatus,
    Category,
    Loan,
    ResponsiblePerson,
    Sector,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username="usuario-operacoes",
        email="usuario-operacoes@example.com",
        password="SenhaSegura@2026",
    )


@pytest.fixture
def technician(db):
    return User.objects.create_user(
        username="tecnico-operacoes",
        email="tecnico-operacoes@example.com",
        password="SenhaSegura@2026",
        role=User.Role.TECHNICIAN,
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="admin-operacoes",
        email="admin-operacoes@example.com",
        password="SenhaSegura@2026",
        role=User.Role.ADMIN,
    )


@pytest.fixture
def origin_sector(db):
    return Sector.objects.create(name="Almoxarifado")


@pytest.fixture
def destination_sector(db):
    return Sector.objects.create(name="Financeiro")


@pytest.fixture
def category(db):
    return Category.objects.create(name="Notebook")


@pytest.fixture
def responsible(destination_sector):
    return ResponsiblePerson.objects.create(
        name="Maria Santos",
        email="maria@example.com",
        employee_id="MAT-001",
        sector=destination_sector,
    )


@pytest.fixture
def asset(origin_sector, category):
    return Asset.objects.create(
        asset_tag="PAT-OPS-001",
        name="Notebook Dell",
        category=category,
        sector=origin_sector,
        status=AssetStatus.objects.get(code="available"),
    )


def authenticate(client, user):
    client.force_authenticate(user=user)


def loan_payload(asset, responsible):
    return {
        "asset": asset.pk,
        "borrower": responsible.pk,
        "expected_return_date": str(timezone.localdate() + timedelta(days=7)),
        "notes": "Uso temporário",
    }


@pytest.mark.django_db
def test_regular_user_can_read_but_cannot_create_responsible(
    api_client, regular_user, responsible, destination_sector
):
    authenticate(api_client, regular_user)

    list_response = api_client.get(reverse("responsible-person-list"))
    create_response = api_client.post(
        reverse("responsible-person-list"),
        {
            "name": "João Lima",
            "email": "joao@example.com",
            "sector": destination_sector.pk,
        },
        format="json",
    )

    assert list_response.status_code == 200
    assert list_response.data["count"] == 1
    assert create_response.status_code == 403


@pytest.mark.django_db
def test_technician_can_create_responsible(api_client, technician, destination_sector):
    authenticate(api_client, technician)

    response = api_client.post(
        reverse("responsible-person-list"),
        {
            "name": "João Lima",
            "email": "JOAO@EXAMPLE.COM",
            "employee_id": "",
            "sector": destination_sector.pk,
        },
        format="json",
    )

    assert response.status_code == 201
    created = ResponsiblePerson.objects.get(pk=response.data["id"])
    assert created.email == "joao@example.com"
    assert created.employee_id is None


@pytest.mark.django_db
def test_loan_updates_asset_and_creates_movement(
    api_client, technician, asset, responsible, origin_sector, destination_sector
):
    authenticate(api_client, technician)

    response = api_client.post(
        reverse("loan-list"), loan_payload(asset, responsible), format="json"
    )

    assert response.status_code == 201
    asset.refresh_from_db()
    assert asset.status.code == "in-use"
    assert asset.responsible == responsible
    assert asset.sector == destination_sector
    movement = AssetMovement.objects.get(loan_id=response.data["id"])
    assert movement.movement_type == AssetMovement.Type.LOAN
    assert movement.from_sector == origin_sector
    assert movement.to_sector == destination_sector
    assert movement.performed_by == technician


@pytest.mark.django_db
def test_asset_cannot_have_two_active_loans(api_client, technician, asset, responsible):
    authenticate(api_client, technician)
    first = api_client.post(reverse("loan-list"), loan_payload(asset, responsible), format="json")
    second = api_client.post(reverse("loan-list"), loan_payload(asset, responsible), format="json")

    assert first.status_code == 201
    assert second.status_code == 400
    assert Loan.objects.filter(asset=asset, returned_at__isnull=True).count() == 1


@pytest.mark.django_db
def test_return_restores_asset_and_registers_history(
    api_client, technician, asset, responsible, origin_sector
):
    authenticate(api_client, technician)
    loan_response = api_client.post(
        reverse("loan-list"), loan_payload(asset, responsible), format="json"
    )

    return_response = api_client.post(
        reverse("loan-return-asset", kwargs={"pk": loan_response.data["id"]}),
        {"notes": "Equipamento devolvido sem avarias"},
        format="json",
    )

    assert return_response.status_code == 200
    asset.refresh_from_db()
    assert asset.status.code == "available"
    assert asset.responsible is None
    assert asset.sector == origin_sector
    assert AssetMovement.objects.filter(asset=asset).count() == 2
    assert AssetMovement.objects.filter(
        asset=asset, movement_type=AssetMovement.Type.RETURN
    ).exists()


@pytest.mark.django_db
def test_loan_cannot_be_returned_twice(api_client, technician, asset, responsible):
    authenticate(api_client, technician)
    loan_response = api_client.post(
        reverse("loan-list"), loan_payload(asset, responsible), format="json"
    )
    url = reverse("loan-return-asset", kwargs={"pk": loan_response.data["id"]})

    first = api_client.post(url, {}, format="json")
    second = api_client.post(url, {}, format="json")

    assert first.status_code == 200
    assert second.status_code == 400


@pytest.mark.django_db
def test_loan_dates_are_validated(api_client, technician, asset, responsible):
    authenticate(api_client, technician)
    payload = loan_payload(asset, responsible)
    payload["loaned_at"] = str(timezone.localdate() + timedelta(days=2))
    payload["expected_return_date"] = str(timezone.localdate() + timedelta(days=1))

    response = api_client.post(reverse("loan-list"), payload, format="json")

    assert response.status_code == 400
    assert "loaned_at" in response.data


@pytest.mark.django_db
def test_loan_history_cannot_be_edited_or_deleted(api_client, admin_user, asset, responsible):
    authenticate(api_client, admin_user)
    loan_response = api_client.post(
        reverse("loan-list"), loan_payload(asset, responsible), format="json"
    )
    url = reverse("loan-detail", kwargs={"pk": loan_response.data["id"]})

    patch_response = api_client.patch(url, {"notes": "alterado"}, format="json")
    delete_response = api_client.delete(url)

    assert patch_response.status_code == 405
    assert delete_response.status_code == 405


@pytest.mark.django_db
def test_transfer_updates_sector_responsible_status_and_history(
    api_client, technician, asset, responsible, destination_sector
):
    authenticate(api_client, technician)

    response = api_client.post(
        reverse("asset-transfer", kwargs={"pk": asset.pk}),
        {
            "to_sector": destination_sector.pk,
            "responsible": responsible.pk,
            "notes": "Transferência definitiva",
        },
        format="json",
    )

    assert response.status_code == 200
    asset.refresh_from_db()
    assert asset.sector == destination_sector
    assert asset.responsible == responsible
    assert asset.status.code == "in-use"
    assert AssetMovement.objects.get(asset=asset).movement_type == AssetMovement.Type.TRANSFER


@pytest.mark.django_db
def test_transfer_is_blocked_during_active_loan(
    api_client, technician, asset, responsible, origin_sector
):
    authenticate(api_client, technician)
    api_client.post(reverse("loan-list"), loan_payload(asset, responsible), format="json")

    response = api_client.post(
        reverse("asset-transfer", kwargs={"pk": asset.pk}),
        {"to_sector": origin_sector.pk, "responsible": None},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_responsible_must_belong_to_destination_sector(
    api_client, technician, asset, responsible, origin_sector
):
    authenticate(api_client, technician)

    response = api_client.post(
        reverse("asset-transfer", kwargs={"pk": asset.pk}),
        {"to_sector": origin_sector.pk, "responsible": responsible.pk},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_direct_asset_sector_update_is_rejected(api_client, technician, asset, destination_sector):
    authenticate(api_client, technician)

    response = api_client.patch(
        reverse("asset-detail", kwargs={"pk": asset.pk}),
        {"sector": destination_sector.pk},
        format="json",
    )

    assert response.status_code == 400
    asset.refresh_from_db()
    assert asset.sector != destination_sector


@pytest.mark.django_db
def test_movements_are_read_only_and_filterable(api_client, technician, asset, responsible):
    authenticate(api_client, technician)
    api_client.post(reverse("loan-list"), loan_payload(asset, responsible), format="json")

    list_response = api_client.get(
        reverse("asset-movement-list"), {"movement_type": AssetMovement.Type.LOAN}
    )
    create_response = api_client.post(
        reverse("asset-movement-list"), {"asset": asset.pk}, format="json"
    )

    assert list_response.status_code == 200
    assert list_response.data["count"] == 1
    assert create_response.status_code == 405


@pytest.mark.django_db
def test_responsible_linked_to_history_cannot_be_deleted(
    api_client, admin_user, asset, responsible
):
    authenticate(api_client, admin_user)
    api_client.post(reverse("loan-list"), loan_payload(asset, responsible), format="json")

    response = api_client.delete(
        reverse("responsible-person-detail", kwargs={"pk": responsible.pk})
    )

    assert response.status_code == 409
    assert ResponsiblePerson.objects.filter(pk=responsible.pk).exists()


@pytest.mark.django_db
def test_admin_can_delete_unused_responsible(api_client, admin_user, responsible):
    authenticate(api_client, admin_user)

    response = api_client.delete(
        reverse("responsible-person-detail", kwargs={"pk": responsible.pk})
    )

    assert response.status_code == 204
