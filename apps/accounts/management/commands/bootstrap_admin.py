import os

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Cria o primeiro administrador a partir das variáveis APP_ADMIN_*"

    @transaction.atomic
    def handle(self, *args, **options):
        username = os.getenv("APP_ADMIN_USERNAME", "").strip()
        email = os.getenv("APP_ADMIN_EMAIL", "").strip().lower()
        password = os.getenv("APP_ADMIN_PASSWORD", "")
        name = os.getenv("APP_ADMIN_NAME", "Administrador").strip()

        if not any((username, email, password)):
            self.stdout.write("Bootstrap de administrador não configurado.")
            return
        if not all((username, email, password)):
            raise CommandError(
                "Defina APP_ADMIN_USERNAME, APP_ADMIN_EMAIL e APP_ADMIN_PASSWORD em conjunto."
            )
        if User.objects.filter(username=username).exists():
            self.stdout.write("Administrador já existe; nenhuma credencial foi alterada.")
            return
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError("APP_ADMIN_EMAIL já pertence a outra conta.")

        first_name, _, last_name = name.partition(" ")
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            raise CommandError(
                "APP_ADMIN_PASSWORD não atende aos requisitos de segurança."
            ) from exc
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS("Administrador inicial criado com sucesso."))
