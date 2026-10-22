from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.inventory.models import (
    Asset,
    AssetAttachment,
    AssetCost,
    AssetMovement,
    AssetStatus,
    Category,
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
        username="usuario-manutencao",
        email="usuario-manutencao@example.com",
        password="SenhaSegura@2026",
    )


@pytest.fixture
def technician(db):
    return User.objects.create_user(
        username="tecnico-manutencao",
        email="tecnico-manutencao@example.com",
        password="SenhaSegura@2026",
        role=User.Role.TECHNICIAN,
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="admin-manutencao",
        email="admin-manutencao@example.com",
        password="SenhaSegura@2026",
        role=User.Role.ADMIN,
    )


@pytest.fixture
def sector(db):
    return Sector.objects.create(name="Infraestrutura")


@pytest.fixture
def category(db):
    return Category.objects.create(name="Servidor")


@pytest.fixture
def asset(sector, category):
    return Asset.objects.create(
        asset_tag="PAT-MAN-001",
        name="Servidor Dell",
        category=category,
        sector=sector,
        status=AssetStatus.objects.get(code="available"),
    )


def authenticate(client, user):
    client.force_authenticate(user=user)


def maintenance_payload(asset):
    return {
        "asset": asset.pk,
        "maintenance_type": Maintenance.Type.CORRECTIVE,
        "description": "Substituição da fonte",
        "provider": "Assistência Técnica",
    }


def create_maintenance(client, asset):
    return client.post(
        reverse("maintenance-list"),
        maintenance_payload(asset),
        format="json",
    )


@pytest.mark.django_db
def test_regular_user_can_read_but_cannot_create_maintenance(
    api_client, regular_user, technician, asset
):
    maintenance = Maintenance.objects.create(
        asset=asset,
        maintenance_type=Maintenance.Type.PREVENTIVE,
        description="Limpeza interna",
        created_by=technician,
    )
    authenticate(api_client, regular_user)

    detail_response = api_client.get(reverse("maintenance-detail", kwargs={"pk": maintenance.pk}))
    create_response = create_maintenance(api_client, asset)

    assert detail_response.status_code == 200
    assert create_response.status_code == 403


@pytest.mark.django_db
def test_create_maintenance_updates_asset_and_registers_movement(api_client, technician, asset):
    authenticate(api_client, technician)

    response = create_maintenance(api_client, asset)

    assert response.status_code == 201
    asset.refresh_from_db()
    assert asset.status.code == "maintenance"
    movement = AssetMovement.objects.get(maintenance_id=response.data["id"])
    assert movement.movement_type == AssetMovement.Type.MAINTENANCE_START
    assert movement.performed_by == technician


@pytest.mark.django_db
def test_asset_cannot_have_two_active_maintenances(api_client, technician, asset):
    authenticate(api_client, technician)

    first = create_maintenance(api_client, asset)
    second = create_maintenance(api_client, asset)

    assert first.status_code == 201
    assert second.status_code == 400
    assert (
        Maintenance.objects.filter(asset=asset, status=Maintenance.Status.IN_PROGRESS).count() == 1
    )


@pytest.mark.django_db
def test_retired_asset_cannot_enter_maintenance(api_client, technician, asset):
    asset.status = AssetStatus.objects.get(code="retired")
    asset.save(update_fields=("status",))
    authenticate(api_client, technician)

    response = create_maintenance(api_client, asset)

    assert response.status_code == 400
    assert not Maintenance.objects.filter(asset=asset).exists()


@pytest.mark.django_db
def test_complete_maintenance_restores_asset_and_creates_cost(api_client, technician, asset):
    authenticate(api_client, technician)
    create_response = create_maintenance(api_client, asset)

    response = api_client.post(
        reverse("maintenance-complete", kwargs={"pk": create_response.data["id"]}),
        {"resolution_notes": "Fonte substituída", "cost": "480.50"},
        format="json",
    )

    assert response.status_code == 200
    asset.refresh_from_db()
    assert asset.status.code == "available"
    maintenance = Maintenance.objects.get(pk=create_response.data["id"])
    assert maintenance.status == Maintenance.Status.COMPLETED
    assert maintenance.cost == Decimal("480.50")
    assert maintenance.completed_at == timezone.localdate()
    cost = AssetCost.objects.get(maintenance=maintenance)
    assert cost.amount == Decimal("480.50")
    assert cost.cost_type == AssetCost.Type.MAINTENANCE
    assert AssetMovement.objects.filter(
        maintenance=maintenance,
        movement_type=AssetMovement.Type.MAINTENANCE_END,
    ).exists()


@pytest.mark.django_db
def test_completion_restores_in_use_status_for_assigned_asset(
    api_client, technician, asset, sector
):
    responsible = ResponsiblePerson.objects.create(
        name="Ana Souza",
        email="ana@example.com",
        sector=sector,
    )
    asset.responsible = responsible
    asset.status = AssetStatus.objects.get(code="in-use")
    asset.save(update_fields=("responsible", "status"))
    authenticate(api_client, technician)
    create_response = create_maintenance(api_client, asset)

    response = api_client.post(
        reverse("maintenance-complete", kwargs={"pk": create_response.data["id"]}),
        {"resolution_notes": "Reparo concluído"},
        format="json",
    )

    assert response.status_code == 200
    asset.refresh_from_db()
    assert asset.status.code == "in-use"
    assert asset.responsible == responsible


@pytest.mark.django_db
def test_cancel_maintenance_restores_asset_without_cost(api_client, technician, asset):
    authenticate(api_client, technician)
    create_response = create_maintenance(api_client, asset)

    response = api_client.post(
        reverse("maintenance-cancel", kwargs={"pk": create_response.data["id"]}),
        {"resolution_notes": "Serviço não autorizado", "cost": "100.00"},
        format="json",
    )

    assert response.status_code == 200
    maintenance = Maintenance.objects.get(pk=create_response.data["id"])
    assert maintenance.status == Maintenance.Status.CANCELLED
    assert maintenance.cost == Decimal("0.00")
    assert not AssetCost.objects.filter(maintenance=maintenance).exists()
    asset.refresh_from_db()
    assert asset.status.code == "available"


@pytest.mark.django_db
def test_maintenance_cannot_be_finished_twice(api_client, technician, asset):
    authenticate(api_client, technician)
    create_response = create_maintenance(api_client, asset)
    url = reverse("maintenance-complete", kwargs={"pk": create_response.data["id"]})

    first = api_client.post(url, {}, format="json")
    second = api_client.post(url, {}, format="json")

    assert first.status_code == 200
    assert second.status_code == 400


@pytest.mark.django_db
def test_maintenance_history_cannot_be_edited_or_deleted(api_client, admin_user, asset):
    authenticate(api_client, admin_user)
    create_response = create_maintenance(api_client, asset)
    url = reverse("maintenance-detail", kwargs={"pk": create_response.data["id"]})

    patch_response = api_client.patch(url, {"description": "alterada"}, format="json")
    delete_response = api_client.delete(url)

    assert patch_response.status_code == 405
    assert delete_response.status_code == 405


@pytest.mark.django_db
def test_warranty_dates_are_validated(api_client, technician, asset):
    authenticate(api_client, technician)

    response = api_client.post(
        reverse("warranty-list"),
        {
            "asset": asset.pk,
            "provider": "Dell",
            "start_date": "2026-10-18",
            "end_date": "2026-10-17",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "end_date" in response.data


@pytest.mark.django_db
def test_technician_can_manage_warranty(api_client, technician, asset):
    authenticate(api_client, technician)

    create_response = api_client.post(
        reverse("warranty-list"),
        {
            "asset": asset.pk,
            "provider": "Dell",
            "contract_number": "GAR-001",
            "start_date": str(timezone.localdate()),
            "end_date": str(timezone.localdate() + timedelta(days=365)),
        },
        format="json",
    )
    update_response = api_client.patch(
        reverse("warranty-detail", kwargs={"pk": create_response.data["id"]}),
        {"coverage_notes": "Peças e mão de obra"},
        format="json",
    )

    assert create_response.status_code == 201
    assert update_response.status_code == 200
    warranty = Warranty.objects.get(pk=create_response.data["id"])
    assert warranty.created_by == technician
    assert warranty.coverage_notes == "Peças e mão de obra"


@pytest.mark.django_db
def test_cost_rejects_invalid_amount_future_date_and_mismatched_maintenance(
    api_client, technician, asset, sector, category
):
    another_asset = Asset.objects.create(
        asset_tag="PAT-MAN-002",
        name="Switch",
        category=category,
        sector=sector,
        status=AssetStatus.objects.get(code="available"),
    )
    maintenance = Maintenance.objects.create(
        asset=another_asset,
        maintenance_type=Maintenance.Type.CORRECTIVE,
        description="Troca de porta",
        created_by=technician,
    )
    authenticate(api_client, technician)

    response = api_client.post(
        reverse("asset-cost-list"),
        {
            "asset": asset.pk,
            "maintenance": maintenance.pk,
            "cost_type": AssetCost.Type.MAINTENANCE,
            "amount": "-1.00",
            "occurred_on": str(timezone.localdate() + timedelta(days=1)),
            "description": "Custo inválido",
        },
        format="json",
    )

    assert response.status_code == 400
    assert {"amount", "occurred_on"}.issubset(response.data)

    mismatch_response = api_client.post(
        reverse("asset-cost-list"),
        {
            "asset": asset.pk,
            "maintenance": maintenance.pk,
            "cost_type": AssetCost.Type.MAINTENANCE,
            "amount": "50.00",
            "description": "Custo em ativo incorreto",
        },
        format="json",
    )
    assert mismatch_response.status_code == 400
    assert "maintenance" in mismatch_response.data


@pytest.mark.django_db
def test_attachment_download_requires_authentication_and_delete_removes_file(
    api_client, technician, admin_user, asset, tmp_path
):
    with override_settings(MEDIA_ROOT=tmp_path):
        authenticate(api_client, technician)
        create_response = api_client.post(
            reverse("asset-attachment-list"),
            {
                "asset": asset.pk,
                "description": "Nota fiscal",
                "file": SimpleUploadedFile(
                    "nota-fiscal.pdf",
                    b"%PDF-1.4 conteudo do arquivo",
                    content_type="application/pdf",
                ),
            },
            format="multipart",
        )

        assert create_response.status_code == 201
        attachment = AssetAttachment.objects.get(pk=create_response.data["id"])
        stored_path = tmp_path / attachment.file.name
        assert stored_path.exists()

        download_url = reverse("asset-attachment-download", kwargs={"pk": attachment.pk})
        download_response = api_client.get(download_url)
        assert download_response.status_code == 200
        assert b"".join(download_response.streaming_content) == b"%PDF-1.4 conteudo do arquivo"

        api_client.force_authenticate(user=None)
        unauthorized_response = api_client.get(download_url)
        assert unauthorized_response.status_code == 401

        authenticate(api_client, admin_user)
        delete_response = api_client.delete(
            reverse("asset-attachment-detail", kwargs={"pk": attachment.pk})
        )
        assert delete_response.status_code == 204
        assert not stored_path.exists()


@pytest.mark.django_db
def test_attachment_rejects_unsupported_file(api_client, technician, asset):
    authenticate(api_client, technician)

    response = api_client.post(
        reverse("asset-attachment-list"),
        {
            "asset": asset.pk,
            "file": SimpleUploadedFile(
                "programa.exe",
                b"arquivo inseguro",
                content_type="application/octet-stream",
            ),
        },
        format="multipart",
    )

    assert response.status_code == 400
    assert "file" in response.data


@pytest.mark.django_db
def test_attachment_rejects_content_disguised_as_pdf(api_client, technician, asset):
    authenticate(api_client, technician)

    response = api_client.post(
        reverse("asset-attachment-list"),
        {
            "asset": asset.pk,
            "file": SimpleUploadedFile(
                "documento.pdf",
                b"executavel disfarcado",
                content_type="application/pdf",
            ),
        },
        format="multipart",
    )

    assert response.status_code == 400
    assert "file" in response.data
