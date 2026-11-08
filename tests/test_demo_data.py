from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.accounts.models import User
from apps.inventory.models import (
    Asset,
    AssetCost,
    AssetMovement,
    Loan,
    Maintenance,
    Notification,
    ResponsiblePerson,
    Warranty,
)


@pytest.fixture
def demo_users(db):
    admin = User.objects.create_user(
        username="admin-demo",
        email="admin-demo@example.com",
        password="SenhaSegura@2026",
        role=User.Role.ADMIN,
    )
    technician = User.objects.create_user(
        username="tecnico-demo",
        email="tecnico-demo@example.com",
        password="SenhaSegura@2026",
    )
    regular = User.objects.create_user(
        username="usuario-demo",
        email="usuario-demo@example.com",
        password="SenhaSegura@2026",
        role=User.Role.TECHNICIAN,
    )
    return admin, technician, regular


def run_seed(*, technician="tecnico-demo", regular="usuario-demo"):
    output = StringIO()
    call_command(
        "seed_demo_data",
        technician=technician,
        regular_user=regular,
        stdout=output,
    )
    return output.getvalue()


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_demo_seed_creates_complete_scenario_and_roles(demo_users):
    _, technician, regular = demo_users

    output = run_seed()

    technician.refresh_from_db()
    regular.refresh_from_db()
    assert technician.role == User.Role.TECHNICIAN
    assert regular.role == User.Role.USER
    assert Asset.objects.filter(asset_tag__startswith="PAT-DEMO-").count() == 6
    assert ResponsiblePerson.objects.count() == 3
    assert Loan.objects.filter(returned_at__isnull=True).count() == 1
    assert Maintenance.objects.filter(status=Maintenance.Status.IN_PROGRESS).count() == 1
    assert Maintenance.objects.filter(status=Maintenance.Status.COMPLETED).count() == 1
    assert Warranty.objects.count() == 2
    assert AssetCost.objects.count() == 7
    assert AssetMovement.objects.count() == 4
    assert Notification.objects.count() == 4
    assert set(Asset.objects.values_list("status__code", flat=True)) == {
        "available",
        "in-use",
        "maintenance",
        "retired",
    }
    assert "6 ativos" in output
    assert "4 novos alertas" in output


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_demo_seed_is_idempotent(demo_users):
    run_seed()
    second_output = run_seed()

    assert Asset.objects.filter(asset_tag__startswith="PAT-DEMO-").count() == 6
    assert Loan.objects.count() == 1
    assert Maintenance.objects.count() == 2
    assert Warranty.objects.count() == 2
    assert AssetCost.objects.count() == 7
    assert AssetMovement.objects.count() == 4
    assert Notification.objects.count() == 4
    assert "0 novos alertas" in second_output


@pytest.mark.django_db
def test_demo_seed_requires_existing_users(demo_users):
    with pytest.raises(CommandError, match='O usuário "inexistente" não foi encontrado'):
        run_seed(technician="inexistente")


@pytest.mark.django_db
def test_demo_seed_requires_distinct_users(demo_users):
    with pytest.raises(CommandError, match="Informe usuários diferentes"):
        run_seed(technician="tecnico-demo", regular="tecnico-demo")
