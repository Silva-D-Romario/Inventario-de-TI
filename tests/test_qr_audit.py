import uuid

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.inventory.models import Asset, AssetStatus, AuditLog, Category, Sector


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username="usuario-auditoria",
        email="usuario-auditoria@example.com",
        password="SenhaSegura@2026",
    )


@pytest.fixture
def technician(db):
    return User.objects.create_user(
        username="tecnico-auditoria",
        email="tecnico-auditoria@example.com",
        password="SenhaSegura@2026",
        role=User.Role.TECHNICIAN,
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="admin-auditoria",
        email="admin-auditoria@example.com",
        password="SenhaSegura@2026",
        role=User.Role.ADMIN,
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name="Equipamento de rede")


@pytest.fixture
def sector(db):
    return Sector.objects.create(name="Data center")


@pytest.fixture
def asset(category, sector):
    return Asset.objects.create(
        asset_tag="PAT-QR-001",
        name="Switch gerenciável",
        category=category,
        sector=sector,
        status=AssetStatus.objects.get(code="available"),
    )


def authenticate(client, user):
    client.force_authenticate(user=user)


def asset_payload(category, sector, tag="PAT-QR-100"):
    return {
        "asset_tag": tag,
        "name": "Roteador corporativo",
        "category": category.pk,
        "sector": sector.pk,
        "status": AssetStatus.objects.get(code="available").pk,
    }


@pytest.mark.django_db
def test_asset_exposes_public_id_and_qr_url(api_client, regular_user, asset):
    authenticate(api_client, regular_user)

    response = api_client.get(reverse("asset-detail", kwargs={"pk": asset.pk}))

    assert response.status_code == 200
    assert uuid.UUID(str(response.data["public_id"])) == asset.public_id
    assert response.data["qr_code_url"].endswith(reverse("asset-qr-code", kwargs={"pk": asset.pk}))


@pytest.mark.django_db
def test_qr_code_requires_authentication(api_client, asset):
    response = api_client.get(reverse("asset-qr-code", kwargs={"pk": asset.pk}))

    assert response.status_code == 401


@pytest.mark.django_db
def test_qr_code_returns_png_label(api_client, regular_user, asset):
    authenticate(api_client, regular_user)

    response = api_client.get(reverse("asset-qr-code", kwargs={"pk": asset.pk}))

    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert f"ativo-{asset.asset_tag}-qrcode.png" in response["Content-Disposition"]
    assert response["Cache-Control"] == "private, max-age=3600"


@pytest.mark.django_db
def test_qr_scan_resolves_asset_and_creates_audit_log(api_client, technician, asset):
    request_id = uuid.uuid4()
    authenticate(api_client, technician)

    response = api_client.get(
        reverse("asset-scan", kwargs={"public_id": asset.public_id}),
        HTTP_X_REQUEST_ID=str(request_id),
        HTTP_USER_AGENT="InventarioScanner/1.0",
        HTTP_X_FORWARDED_FOR="192.168.0.15, 10.0.0.1",
    )

    assert response.status_code == 200
    assert response.data["id"] == asset.pk
    log = AuditLog.objects.get(action=AuditLog.Action.SCAN)
    assert log.actor == technician
    assert log.resource_type == "inventory.asset"
    assert log.object_id == str(asset.pk)
    assert log.changes == {"event": "QR_SCAN"}
    assert log.ip_address == "192.168.0.15"
    assert log.user_agent == "InventarioScanner/1.0"
    assert log.request_id == request_id


@pytest.mark.django_db
def test_unknown_qr_code_returns_not_found_without_audit(api_client, regular_user):
    authenticate(api_client, regular_user)

    response = api_client.get(reverse("asset-scan", kwargs={"public_id": uuid.uuid4()}))

    assert response.status_code == 404
    assert not AuditLog.objects.exists()


@pytest.mark.django_db
def test_asset_crud_creates_immutable_audit_history(api_client, admin_user, category, sector):
    authenticate(api_client, admin_user)
    create_response = api_client.post(
        reverse("asset-list"),
        asset_payload(category, sector),
        format="json",
        HTTP_USER_AGENT="pytest",
    )
    asset_id = create_response.data["id"]

    update_response = api_client.patch(
        reverse("asset-detail", kwargs={"pk": asset_id}),
        {"name": "Roteador atualizado"},
        format="json",
    )
    delete_response = api_client.delete(reverse("asset-detail", kwargs={"pk": asset_id}))

    assert create_response.status_code == 201
    assert update_response.status_code == 200
    assert delete_response.status_code == 204
    logs = AuditLog.objects.filter(
        resource_type="inventory.asset",
        object_id=str(asset_id),
    ).order_by("created_at", "id")
    assert list(logs.values_list("action", flat=True)) == [
        AuditLog.Action.CREATE,
        AuditLog.Action.UPDATE,
        AuditLog.Action.DELETE,
    ]
    assert logs[0].actor == admin_user
    assert logs[0].changes["fields"]["asset_tag"] == "PAT-QR-100"
    assert logs[1].changes["name"] == {
        "from": "Roteador corporativo",
        "to": "Roteador atualizado",
    }


@pytest.mark.django_db
def test_failed_protected_delete_is_not_audited(api_client, admin_user, category, asset):
    authenticate(api_client, admin_user)

    response = api_client.delete(reverse("category-detail", kwargs={"pk": category.pk}))

    assert response.status_code == 409
    assert not AuditLog.objects.filter(
        action=AuditLog.Action.DELETE,
        resource_type="inventory.category",
        object_id=str(category.pk),
    ).exists()


@pytest.mark.django_db
def test_transfer_creates_operational_audit_log(api_client, technician, asset):
    destination = Sector.objects.create(name="Filial")
    authenticate(api_client, technician)

    response = api_client.post(
        reverse("asset-transfer", kwargs={"pk": asset.pk}),
        {"to_sector": destination.pk, "responsible": None, "notes": "Mudança de local"},
        format="json",
    )

    assert response.status_code == 200
    log = AuditLog.objects.get(action=AuditLog.Action.ACTION)
    assert log.resource_type == "inventory.asset"
    assert log.changes == {
        "event": "TRANSFER",
        "to_sector": destination.pk,
        "responsible": None,
        "notes": "Mudança de local",
    }


@pytest.mark.django_db
def test_only_admin_can_read_audit_logs(api_client, regular_user, technician, admin_user, asset):
    AuditLog.objects.create(
        actor=technician,
        action=AuditLog.Action.UPDATE,
        resource_type="inventory.asset",
        object_id=str(asset.pk),
        object_repr=str(asset),
    )
    url = reverse("audit-log-list")

    authenticate(api_client, regular_user)
    regular_response = api_client.get(url)
    authenticate(api_client, technician)
    technician_response = api_client.get(url)
    authenticate(api_client, admin_user)
    admin_response = api_client.get(url, {"action": AuditLog.Action.UPDATE})

    assert regular_response.status_code == 403
    assert technician_response.status_code == 403
    assert admin_response.status_code == 200
    assert admin_response.data["count"] == 1
    assert admin_response.data["results"][0]["actor_username"] == technician.username


@pytest.mark.django_db
def test_audit_api_is_read_only(api_client, admin_user, asset):
    log = AuditLog.objects.create(
        actor=admin_user,
        action=AuditLog.Action.CREATE,
        resource_type="inventory.asset",
        object_id=str(asset.pk),
        object_repr=str(asset),
    )
    authenticate(api_client, admin_user)

    create_response = api_client.post(reverse("audit-log-list"), {}, format="json")
    update_response = api_client.patch(
        reverse("audit-log-detail", kwargs={"pk": log.pk}),
        {"changes": {"tampered": True}},
        format="json",
    )
    delete_response = api_client.delete(reverse("audit-log-detail", kwargs={"pk": log.pk}))

    assert create_response.status_code == 405
    assert update_response.status_code == 405
    assert delete_response.status_code == 405
    assert AuditLog.objects.filter(pk=log.pk).exists()
