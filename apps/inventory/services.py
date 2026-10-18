from django.db import transaction
from django.utils import timezone

from apps.inventory.models import (
    Asset,
    AssetCost,
    AssetMovement,
    AssetStatus,
    Loan,
    Maintenance,
)


class InventoryOperationError(Exception):
    pass


@transaction.atomic
def create_loan(*, asset, borrower, loaned_at, expected_return_date, notes, user):
    locked_asset = (
        Asset.objects.select_for_update().select_related("status", "sector").get(pk=asset.pk)
    )
    if Loan.objects.filter(asset=locked_asset, returned_at__isnull=True).exists():
        raise InventoryOperationError("Este ativo já possui um empréstimo ativo.")
    if locked_asset.status.code != "available":
        raise InventoryOperationError("Somente ativos disponíveis podem ser emprestados.")
    if not borrower.is_active:
        raise InventoryOperationError("O responsável selecionado está inativo.")

    origin_sector = locked_asset.sector
    loan = Loan.objects.create(
        asset=locked_asset,
        borrower=borrower,
        loaned_at=loaned_at,
        expected_return_date=expected_return_date,
        notes=notes,
        created_by=user,
    )
    locked_asset.status = AssetStatus.objects.get(code="in-use")
    locked_asset.sector = borrower.sector
    locked_asset.responsible = borrower
    locked_asset.save(update_fields=("status", "sector", "responsible", "updated_at"))
    AssetMovement.objects.create(
        asset=locked_asset,
        movement_type=AssetMovement.Type.LOAN,
        from_sector=origin_sector,
        to_sector=borrower.sector,
        responsible=borrower,
        loan=loan,
        performed_by=user,
        notes=notes,
    )
    return loan


@transaction.atomic
def return_loan(*, loan, notes, user):
    locked_loan = (
        Loan.objects.select_for_update().select_related("asset", "borrower").get(pk=loan.pk)
    )
    if locked_loan.returned_at is not None:
        raise InventoryOperationError("Este empréstimo já foi devolvido.")

    locked_asset = Asset.objects.select_for_update().get(pk=locked_loan.asset_id)
    loan_movement = locked_loan.movements.get(movement_type=AssetMovement.Type.LOAN)
    current_sector = locked_asset.sector
    locked_loan.returned_at = timezone.localdate()
    locked_loan.save(update_fields=("returned_at", "updated_at"))
    locked_asset.status = AssetStatus.objects.get(code="available")
    locked_asset.sector = loan_movement.from_sector
    locked_asset.responsible = None
    locked_asset.save(update_fields=("status", "sector", "responsible", "updated_at"))
    AssetMovement.objects.create(
        asset=locked_asset,
        movement_type=AssetMovement.Type.RETURN,
        from_sector=current_sector,
        to_sector=loan_movement.from_sector,
        responsible=locked_loan.borrower,
        loan=locked_loan,
        performed_by=user,
        notes=notes,
    )
    return locked_loan


@transaction.atomic
def transfer_asset(*, asset, to_sector, responsible, notes, user):
    locked_asset = (
        Asset.objects.select_for_update().select_related("status", "sector").get(pk=asset.pk)
    )
    if Loan.objects.filter(asset=locked_asset, returned_at__isnull=True).exists():
        raise InventoryOperationError("Devolva o empréstimo ativo antes de transferir o ativo.")
    if locked_asset.status.code not in {"available", "in-use"}:
        raise InventoryOperationError(
            "Ativos em manutenção ou baixados não podem ser transferidos."
        )
    if responsible and not responsible.is_active:
        raise InventoryOperationError("O responsável selecionado está inativo.")
    if responsible and responsible.sector_id != to_sector.pk:
        raise InventoryOperationError("O responsável deve pertencer ao setor de destino.")
    if locked_asset.sector_id == to_sector.pk and locked_asset.responsible_id == (
        responsible.pk if responsible else None
    ):
        raise InventoryOperationError("Informe um setor ou responsável diferente do atual.")

    origin_sector = locked_asset.sector
    movement_type = (
        AssetMovement.Type.TRANSFER
        if locked_asset.sector_id != to_sector.pk
        else AssetMovement.Type.ASSIGNMENT
    )
    locked_asset.sector = to_sector
    locked_asset.responsible = responsible
    locked_asset.status = AssetStatus.objects.get(code="in-use" if responsible else "available")
    locked_asset.save(update_fields=("sector", "responsible", "status", "updated_at"))
    movement = AssetMovement.objects.create(
        asset=locked_asset,
        movement_type=movement_type,
        from_sector=origin_sector,
        to_sector=to_sector,
        responsible=responsible,
        performed_by=user,
        notes=notes,
    )
    return locked_asset, movement


@transaction.atomic
def create_maintenance(*, asset, maintenance_type, description, provider, started_at, user):
    locked_asset = (
        Asset.objects.select_for_update().select_related("status", "sector").get(pk=asset.pk)
    )
    if Maintenance.objects.filter(
        asset=locked_asset,
        status=Maintenance.Status.IN_PROGRESS,
    ).exists():
        raise InventoryOperationError("Este ativo já possui uma manutenção em andamento.")
    if Loan.objects.filter(asset=locked_asset, returned_at__isnull=True).exists():
        raise InventoryOperationError("Devolva o empréstimo ativo antes de iniciar a manutenção.")
    if locked_asset.status.code not in {"available", "in-use"}:
        raise InventoryOperationError(
            "Somente ativos disponíveis ou em uso podem entrar em manutenção."
        )

    maintenance = Maintenance.objects.create(
        asset=locked_asset,
        maintenance_type=maintenance_type,
        description=description,
        provider=provider,
        started_at=started_at,
        created_by=user,
    )
    locked_asset.status = AssetStatus.objects.get(code="maintenance")
    locked_asset.save(update_fields=("status", "updated_at"))
    AssetMovement.objects.create(
        asset=locked_asset,
        movement_type=AssetMovement.Type.MAINTENANCE_START,
        from_sector=locked_asset.sector,
        to_sector=locked_asset.sector,
        responsible=locked_asset.responsible,
        maintenance=maintenance,
        performed_by=user,
        notes=description,
    )
    return maintenance


@transaction.atomic
def finish_maintenance(*, maintenance, final_status, resolution_notes, cost, user):
    locked_maintenance = (
        Maintenance.objects.select_for_update().select_related("asset").get(pk=maintenance.pk)
    )
    if locked_maintenance.status != Maintenance.Status.IN_PROGRESS:
        raise InventoryOperationError("Esta manutenção já foi encerrada.")
    if final_status not in {
        Maintenance.Status.COMPLETED,
        Maintenance.Status.CANCELLED,
    }:
        raise InventoryOperationError("Informe um status final válido para a manutenção.")

    locked_asset = Asset.objects.select_for_update().get(pk=locked_maintenance.asset_id)
    locked_maintenance.status = final_status
    locked_maintenance.completed_at = timezone.localdate()
    locked_maintenance.resolution_notes = resolution_notes
    locked_maintenance.cost = cost
    locked_maintenance.save(
        update_fields=(
            "status",
            "completed_at",
            "resolution_notes",
            "cost",
            "updated_at",
        )
    )

    locked_asset.status = AssetStatus.objects.get(
        code="in-use" if locked_asset.responsible_id else "available"
    )
    locked_asset.save(update_fields=("status", "updated_at"))
    AssetMovement.objects.create(
        asset=locked_asset,
        movement_type=AssetMovement.Type.MAINTENANCE_END,
        from_sector=locked_asset.sector,
        to_sector=locked_asset.sector,
        responsible=locked_asset.responsible,
        maintenance=locked_maintenance,
        performed_by=user,
        notes=resolution_notes,
    )
    if final_status == Maintenance.Status.COMPLETED and cost > 0:
        AssetCost.objects.create(
            asset=locked_asset,
            maintenance=locked_maintenance,
            cost_type=AssetCost.Type.MAINTENANCE,
            amount=cost,
            occurred_on=locked_maintenance.completed_at,
            description=f"Manutenção: {locked_maintenance.description}",
            created_by=user,
        )
    return locked_maintenance
