from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.inventory.models import (
    Asset,
    AssetCost,
    AssetMovement,
    AssetStatus,
    Category,
    Loan,
    Maintenance,
    ResponsiblePerson,
    Sector,
    Warranty,
)
from apps.inventory.tasks import generate_inventory_alerts


class DemoSeedError(Exception):
    pass


@dataclass(frozen=True)
class DemoSeedResult:
    assets: int
    categories: int
    sectors: int
    responsible_people: int
    loans: int
    maintenances: int
    warranties: int
    costs: int
    alerts_created: int


def _required_user(username):
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist as exc:
        raise DemoSeedError(f'O usuário "{username}" não foi encontrado.') from exc


def _seed_references():
    category_data = {
        "Desktop": "Computadores de mesa e estações de trabalho.",
        "Impressora": "Impressoras e equipamentos multifuncionais.",
        "Monitor": "Monitores e telas para estações de trabalho.",
        "Notebook": "Computadores portáteis corporativos.",
        "Rede": "Switches, roteadores e equipamentos de conectividade.",
        "Tablet": "Dispositivos móveis utilizados pelas equipes.",
    }
    categories = {}
    for name, description in category_data.items():
        categories[name], _ = Category.objects.update_or_create(
            name=name,
            defaults={"description": description, "is_active": True},
        )

    sector_data = {
        "Administrativo": "Bloco A",
        "Diretoria": "Bloco A - 1º andar",
        "Financeiro": "Bloco B",
        "Tecnologia da Informação": "Bloco de TI",
    }
    sectors = {}
    for name, location in sector_data.items():
        sectors[name], _ = Sector.objects.update_or_create(
            name=name,
            defaults={"location": location, "is_active": True},
        )
    return categories, sectors


def _seed_responsible_people(sectors):
    people_data = (
        ("Ana Souza", "ana.souza@example.com", "FIN-001", "Financeiro"),
        ("Carlos Lima", "carlos.lima@example.com", "ADM-001", "Administrativo"),
        ("Helena Costa", "helena.costa@example.com", "DIR-001", "Diretoria"),
    )
    people = {}
    for name, email, employee_id, sector_name in people_data:
        people[email], _ = ResponsiblePerson.objects.update_or_create(
            email=email,
            defaults={
                "name": name,
                "employee_id": employee_id,
                "phone": "(79) 99999-0000",
                "sector": sectors[sector_name],
                "is_active": True,
            },
        )
    return people


def _seed_assets(*, categories, sectors, people, technician, today):
    statuses = {status.code: status for status in AssetStatus.objects.all()}
    asset_data = (
        {
            "asset_tag": "PAT-DEMO-001",
            "name": "Notebook Dell Latitude 5440",
            "category": "Notebook",
            "sector": "Tecnologia da Informação",
            "status": "available",
            "serial_number": "DEMO-DELL-5440-001",
            "manufacturer": "Dell",
            "model": "Latitude 5440",
            "value": Decimal("5290.00"),
        },
        {
            "asset_tag": "PAT-DEMO-002",
            "name": "Desktop Lenovo ThinkCentre",
            "category": "Desktop",
            "sector": "Financeiro",
            "status": "in-use",
            "responsible": "ana.souza@example.com",
            "serial_number": "DEMO-LENOVO-M70-002",
            "manufacturer": "Lenovo",
            "model": "ThinkCentre M70",
            "value": Decimal("4100.00"),
        },
        {
            "asset_tag": "PAT-DEMO-003",
            "name": "Impressora HP LaserJet Pro",
            "category": "Impressora",
            "sector": "Administrativo",
            "status": "maintenance",
            "responsible": "carlos.lima@example.com",
            "serial_number": "DEMO-HP-M428-003",
            "manufacturer": "HP",
            "model": "LaserJet Pro M428",
            "value": Decimal("2850.00"),
        },
        {
            "asset_tag": "PAT-DEMO-004",
            "name": "Monitor LG 24 polegadas",
            "category": "Monitor",
            "sector": "Tecnologia da Informação",
            "status": "retired",
            "serial_number": "DEMO-LG-24-004",
            "manufacturer": "LG",
            "model": "24MP400",
            "value": Decimal("790.00"),
        },
        {
            "asset_tag": "PAT-DEMO-005",
            "name": "Switch Cisco CBS250",
            "category": "Rede",
            "sector": "Tecnologia da Informação",
            "status": "available",
            "serial_number": "DEMO-CISCO-CBS250-005",
            "manufacturer": "Cisco",
            "model": "CBS250-24T-4G",
            "value": Decimal("3200.00"),
        },
        {
            "asset_tag": "PAT-DEMO-006",
            "name": "Tablet Samsung Galaxy Tab",
            "category": "Tablet",
            "sector": "Diretoria",
            "status": "in-use",
            "responsible": "helena.costa@example.com",
            "serial_number": "DEMO-SAMSUNG-TAB-006",
            "manufacturer": "Samsung",
            "model": "Galaxy Tab S9 FE",
            "value": Decimal("2690.00"),
        },
    )

    assets = {}
    for item in asset_data:
        responsible_email = item.get("responsible")
        asset, _ = Asset.objects.update_or_create(
            asset_tag=item["asset_tag"],
            defaults={
                "name": item["name"],
                "category": categories[item["category"]],
                "sector": sectors[item["sector"]],
                "status": statuses[item["status"]],
                "responsible": people.get(responsible_email),
                "serial_number": item["serial_number"],
                "manufacturer": item["manufacturer"],
                "model": item["model"],
                "acquisition_date": today - timedelta(days=180),
                "purchase_value": item["value"],
                "notes": "Registro criado pelo cenário demonstrativo.",
                "created_by": technician,
            },
        )
        assets[item["asset_tag"]] = asset
        AssetCost.objects.update_or_create(
            asset=asset,
            cost_type=AssetCost.Type.PURCHASE,
            description="[DEMO] Aquisição do ativo",
            defaults={
                "amount": item["value"],
                "occurred_on": today - timedelta(days=180),
                "created_by": technician,
            },
        )
    return assets


def _seed_operations(*, assets, sectors, people, technician, today):
    desktop = assets["PAT-DEMO-002"]
    loan = Loan.objects.filter(asset=desktop, returned_at__isnull=True).first()
    if loan is None:
        loan = Loan(asset=desktop)
    loan.borrower = people["ana.souza@example.com"]
    loan.loaned_at = today - timedelta(days=14)
    loan.expected_return_date = today - timedelta(days=2)
    loan.returned_at = None
    loan.notes = "[DEMO] Empréstimo vencido para validar alertas."
    loan.created_by = technician
    loan.save()
    AssetMovement.objects.update_or_create(
        loan=loan,
        movement_type=AssetMovement.Type.LOAN,
        defaults={
            "asset": desktop,
            "from_sector": sectors["Tecnologia da Informação"],
            "to_sector": sectors["Financeiro"],
            "responsible": people["ana.souza@example.com"],
            "performed_by": technician,
            "notes": loan.notes,
        },
    )

    printer = assets["PAT-DEMO-003"]
    active_maintenance = Maintenance.objects.filter(
        asset=printer,
        status=Maintenance.Status.IN_PROGRESS,
    ).first()
    if active_maintenance is None:
        active_maintenance = Maintenance(asset=printer)
    active_maintenance.maintenance_type = Maintenance.Type.CORRECTIVE
    active_maintenance.status = Maintenance.Status.IN_PROGRESS
    active_maintenance.description = "[DEMO] Substituição do kit fusor."
    active_maintenance.provider = "Assistência Técnica Exemplo"
    active_maintenance.started_at = today - timedelta(days=3)
    active_maintenance.completed_at = None
    active_maintenance.cost = Decimal("0.00")
    active_maintenance.resolution_notes = ""
    active_maintenance.created_by = technician
    active_maintenance.save()
    AssetMovement.objects.update_or_create(
        maintenance=active_maintenance,
        movement_type=AssetMovement.Type.MAINTENANCE_START,
        defaults={
            "asset": printer,
            "from_sector": printer.sector,
            "to_sector": printer.sector,
            "responsible": printer.responsible,
            "performed_by": technician,
            "notes": active_maintenance.description,
        },
    )

    notebook = assets["PAT-DEMO-001"]
    completed_maintenance, _ = Maintenance.objects.update_or_create(
        asset=notebook,
        description="[DEMO] Limpeza preventiva e atualização de firmware.",
        defaults={
            "maintenance_type": Maintenance.Type.PREVENTIVE,
            "status": Maintenance.Status.COMPLETED,
            "provider": "Equipe interna de TI",
            "started_at": today - timedelta(days=45),
            "completed_at": today - timedelta(days=44),
            "cost": Decimal("180.00"),
            "resolution_notes": "Equipamento revisado e liberado.",
            "created_by": technician,
        },
    )
    AssetMovement.objects.update_or_create(
        maintenance=completed_maintenance,
        movement_type=AssetMovement.Type.MAINTENANCE_END,
        defaults={
            "asset": notebook,
            "from_sector": notebook.sector,
            "to_sector": notebook.sector,
            "performed_by": technician,
            "notes": completed_maintenance.resolution_notes,
        },
    )
    AssetCost.objects.update_or_create(
        asset=notebook,
        maintenance=completed_maintenance,
        cost_type=AssetCost.Type.MAINTENANCE,
        description="[DEMO] Manutenção preventiva",
        defaults={
            "amount": completed_maintenance.cost,
            "occurred_on": completed_maintenance.completed_at,
            "created_by": technician,
        },
    )

    tablet = assets["PAT-DEMO-006"]
    AssetMovement.objects.update_or_create(
        asset=tablet,
        movement_type=AssetMovement.Type.ASSIGNMENT,
        notes="[DEMO] Atribuição do tablet à diretoria.",
        defaults={
            "from_sector": sectors["Tecnologia da Informação"],
            "to_sector": sectors["Diretoria"],
            "responsible": people["helena.costa@example.com"],
            "performed_by": technician,
        },
    )


def _seed_warranties(*, assets, technician, today):
    Warranty.objects.update_or_create(
        asset=assets["PAT-DEMO-001"],
        contract_number="DEMO-GARANTIA-001",
        defaults={
            "provider": "Dell Brasil",
            "start_date": today - timedelta(days=180),
            "end_date": today + timedelta(days=185),
            "coverage_notes": "Suporte no local e substituição de componentes.",
            "created_by": technician,
        },
    )
    Warranty.objects.update_or_create(
        asset=assets["PAT-DEMO-005"],
        contract_number="DEMO-GARANTIA-005",
        defaults={
            "provider": "Cisco Brasil",
            "start_date": today - timedelta(days=350),
            "end_date": today + timedelta(days=15),
            "coverage_notes": "Garantia próxima do vencimento para validar alertas.",
            "created_by": technician,
        },
    )


@transaction.atomic
def seed_demo_data(*, technician_username, regular_username, create_alerts=True):
    if technician_username == regular_username:
        raise DemoSeedError("Informe usuários diferentes para técnico e usuário comum.")

    technician = _required_user(technician_username)
    regular_user = _required_user(regular_username)
    technician.role = User.Role.TECHNICIAN
    technician.is_active = True
    technician.save(update_fields=("role", "is_active"))
    regular_user.role = User.Role.USER
    regular_user.is_active = True
    regular_user.save(update_fields=("role", "is_active"))

    today = timezone.localdate()
    categories, sectors = _seed_references()
    people = _seed_responsible_people(sectors)
    assets = _seed_assets(
        categories=categories,
        sectors=sectors,
        people=people,
        technician=technician,
        today=today,
    )
    _seed_operations(
        assets=assets,
        sectors=sectors,
        people=people,
        technician=technician,
        today=today,
    )
    _seed_warranties(assets=assets, technician=technician, today=today)

    alert_result = generate_inventory_alerts() if create_alerts else {"created": 0}
    demo_assets = Asset.objects.filter(asset_tag__startswith="PAT-DEMO-")
    return DemoSeedResult(
        assets=demo_assets.count(),
        categories=Category.objects.filter(name__in=categories).count(),
        sectors=Sector.objects.filter(name__in=sectors).count(),
        responsible_people=ResponsiblePerson.objects.filter(email__in=people).count(),
        loans=Loan.objects.filter(asset__in=demo_assets).count(),
        maintenances=Maintenance.objects.filter(asset__in=demo_assets).count(),
        warranties=Warranty.objects.filter(asset__in=demo_assets).count(),
        costs=AssetCost.objects.filter(asset__in=demo_assets).count(),
        alerts_created=alert_result["created"],
    )
