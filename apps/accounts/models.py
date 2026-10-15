from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        TECHNICIAN = "TECHNICIAN", "Técnico"
        USER = "USER", "Usuário"

    email = models.EmailField("e-mail", unique=True)
    role = models.CharField(
        "perfil de acesso",
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
    )

    REQUIRED_FIELDS = ["email"]

    @property
    def is_admin(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def is_technician(self):
        return self.role == self.Role.TECHNICIAN

    def __str__(self):
        return self.get_full_name() or self.username
