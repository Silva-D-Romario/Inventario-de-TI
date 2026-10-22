from datetime import timedelta

import pytest
from django.conf import settings
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.inventory.models import (
    Asset,
    AssetStatus,
    Category,
    Loan,
    Notification,
    ResponsiblePerson,
    Sector,
    Warranty,
)
from apps.inventory.tasks import generate_inventory_alerts


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username="usuario-notificacao",
        email="usuario-notificacao@example.com",
        password="SenhaSegura@2026",
    )


@pytest.fixture
def technician(db):
    return User.objects.create_user(
        username="tecnico-notificacao",
        email="tecnico-notificacao@example.com",
        password="SenhaSegura@2026",
        role=User.Role.TECHNICIAN,
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="admin-notificacao",
        email="admin-notificacao@example.com",
        password="SenhaSegura@2026",
        role=User.Role.ADMIN,
    )


@pytest.fixture
def alert_data(db, technician, admin_user, regular_user):
    today = timezone.localdate()
    sector = Sector.objects.create(name="Operações")
    category = Category.objects.create(name="Equipamentos")
    status = AssetStatus.objects.get(code="available")
    first_asset = Asset.objects.create(
        asset_tag="PAT-ALERT-001",
        name="Notebook",
        category=category,
        sector=sector,
        status=status,
    )
    second_asset = Asset.objects.create(
        asset_tag="PAT-ALERT-002",
        name="Impressora",
        category=category,
        sector=sector,
        status=status,
    )
    borrower = ResponsiblePerson.objects.create(
        name="Carlos Lima",
        email="carlos.alertas@example.com",
        sector=sector,
    )
    overdue_loan = Loan.objects.create(
        asset=first_asset,
        borrower=borrower,
        loaned_at=today - timedelta(days=10),
        expected_return_date=today - timedelta(days=1),
        created_by=technician,
    )
    Loan.objects.create(
        asset=second_asset,
        borrower=borrower,
        loaned_at=today - timedelta(days=20),
        expected_return_date=today - timedelta(days=10),
        returned_at=today - timedelta(days=9),
        created_by=technician,
    )
    expiring_warranty = Warranty.objects.create(
        asset=second_asset,
        provider="Fabricante",
        start_date=today - timedelta(days=300),
        end_date=today + timedelta(days=10),
        created_by=admin_user,
    )
    Warranty.objects.create(
        asset=first_asset,
        provider="Garantia antiga",
        start_date=today - timedelta(days=500),
        end_date=today - timedelta(days=1),
        created_by=admin_user,
    )
    inactive_technician = User.objects.create_user(
        username="tecnico-inativo",
        email="tecnico-inativo@example.com",
        password="SenhaSegura@2026",
        role=User.Role.TECHNICIAN,
        is_active=False,
    )
    return {
        "overdue_loan": overdue_loan,
        "expiring_warranty": expiring_warranty,
        "inactive_technician": inactive_technician,
        "technician": technician,
        "admin": admin_user,
        "regular": regular_user,
    }


def authenticate(client, user):
    client.force_authenticate(user=user)


def create_notification(recipient, dedup_key, title="Alerta"):
    return Notification.objects.create(
        recipient=recipient,
        alert_type=Notification.Type.OVERDUE_LOAN,
        title=title,
        message="Mensagem do alerta",
        resource_type="inventory.loan",
        resource_id="1",
        dedup_key=dedup_key,
    )


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_task_creates_and_emails_alerts_only_for_operational_users(alert_data):
    result = generate_inventory_alerts()

    assert result == {
        "created": 4,
        "overdue_loans": 1,
        "expiring_warranties": 1,
        "recipients": 2,
    }
    assert Notification.objects.count() == 4
    assert len(mail.outbox) == 4
    assert set(Notification.objects.values_list("recipient", flat=True)) == {
        alert_data["technician"].pk,
        alert_data["admin"].pk,
    }
    assert set(Notification.objects.values_list("alert_type", flat=True)) == {
        Notification.Type.OVERDUE_LOAN,
        Notification.Type.WARRANTY_EXPIRING,
    }
    assert set(Notification.objects.values_list("resource_type", flat=True)) == {
        "inventory.loan",
        "inventory.warranty",
    }


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_task_is_idempotent(alert_data):
    first_result = generate_inventory_alerts()
    second_result = generate_inventory_alerts()

    assert first_result["created"] == 4
    assert second_result["created"] == 0
    assert Notification.objects.count() == 4
    assert len(mail.outbox) == 4


@pytest.mark.django_db
def test_notification_list_requires_authentication(api_client):
    response = api_client.get(reverse("notification-list"))

    assert response.status_code == 401


@pytest.mark.django_db
def test_user_only_reads_own_notifications(api_client, regular_user, technician):
    own = create_notification(regular_user, "own-alert")
    other = create_notification(technician, "other-alert")
    authenticate(api_client, regular_user)

    list_response = api_client.get(reverse("notification-list"))
    other_response = api_client.get(reverse("notification-detail", kwargs={"pk": other.pk}))

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.data["results"]] == [own.pk]
    assert other_response.status_code == 404


@pytest.mark.django_db
def test_user_marks_one_notification_as_read(api_client, regular_user):
    notification = create_notification(regular_user, "read-one")
    authenticate(api_client, regular_user)

    response = api_client.post(reverse("notification-mark-read", kwargs={"pk": notification.pk}))

    assert response.status_code == 200
    assert response.data["is_read"] is True
    notification.refresh_from_db()
    assert notification.read_at is not None


@pytest.mark.django_db
def test_user_marks_all_own_notifications_as_read(api_client, regular_user, technician):
    first = create_notification(regular_user, "read-all-1")
    second = create_notification(regular_user, "read-all-2")
    other = create_notification(technician, "read-all-other")
    authenticate(api_client, regular_user)

    response = api_client.post(reverse("notification-mark-all-read"))

    assert response.status_code == 200
    assert response.data == {"updated": 2}
    assert not Notification.objects.filter(
        pk__in=(first.pk, second.pk), read_at__isnull=True
    ).exists()
    assert Notification.objects.filter(pk=other.pk, read_at__isnull=True).exists()


@pytest.mark.django_db
def test_notification_filters_unread_and_type(api_client, regular_user):
    unread = create_notification(regular_user, "unread")
    read = create_notification(regular_user, "read")
    read.read_at = timezone.now()
    read.save(update_fields=("read_at",))
    authenticate(api_client, regular_user)

    response = api_client.get(
        reverse("notification-list"),
        {"read_at__isnull": "true", "alert_type": Notification.Type.OVERDUE_LOAN},
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.data["results"]] == [unread.pk]


def test_daily_alert_schedule_is_configured():
    schedule = settings.CELERY_BEAT_SCHEDULE["inventory-alerts-daily"]

    assert schedule["task"] == "inventory.generate_alerts"
