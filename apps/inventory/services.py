from django.db import transaction
from django.utils import timezone

from apps.inventory.models import Asset, AssetMovement, AssetStatus, Loan


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
