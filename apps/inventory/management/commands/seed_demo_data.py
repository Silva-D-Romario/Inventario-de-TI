from django.core.management.base import BaseCommand, CommandError

from apps.inventory.demo import DemoSeedError, seed_demo_data


class Command(BaseCommand):
    help = "Cria ou atualiza um cenário demonstrativo completo e idempotente"

    def add_arguments(self, parser):
        parser.add_argument("--technician", default="romario.tech")
        parser.add_argument("--regular-user", default="romario.default")
        parser.add_argument(
            "--skip-alerts",
            action="store_true",
            help="Não gera notificações de empréstimo e garantia.",
        )

    def handle(self, *args, **options):
        try:
            result = seed_demo_data(
                technician_username=options["technician"],
                regular_username=options["regular_user"],
                create_alerts=not options["skip_alerts"],
            )
        except DemoSeedError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Cenário demonstrativo pronto: "
                f"{result.assets} ativos, {result.loans} empréstimo, "
                f"{result.maintenances} manutenções, {result.warranties} garantias, "
                f"{result.costs} custos e {result.alerts_created} novos alertas."
            )
        )
