from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models.functions import Lower


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    name = models.CharField("nome", max_length=100)
    description = models.TextField("descrição", blank=True)
    is_active = models.BooleanField("ativo", default=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "categoria"
        verbose_name_plural = "categorias"
        constraints = [
            models.UniqueConstraint(Lower("name"), name="inventory_category_name_ci_unique")
        ]

    def __str__(self):
        return self.name


class Sector(TimeStampedModel):
    name = models.CharField("nome", max_length=100)
    location = models.CharField("localização", max_length=150, blank=True)
    is_active = models.BooleanField("ativo", default=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "setor"
        verbose_name_plural = "setores"
        constraints = [
            models.UniqueConstraint(Lower("name"), name="inventory_sector_name_ci_unique")
        ]

    def __str__(self):
        return self.name


class AssetStatus(TimeStampedModel):
    code = models.SlugField("código", max_length=40, unique=True)
    name = models.CharField("nome", max_length=80)
    color = models.CharField(
        "cor",
        max_length=7,
        default="#64748B",
        validators=[
            RegexValidator(
                regex=r"^#[0-9A-Fa-f]{6}$",
                message="Informe uma cor hexadecimal no formato #RRGGBB.",
            )
        ],
    )
    is_active = models.BooleanField("ativo", default=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "status do ativo"
        verbose_name_plural = "status dos ativos"
        constraints = [
            models.UniqueConstraint(Lower("name"), name="inventory_status_name_ci_unique")
        ]

    def __str__(self):
        return self.name


class Asset(TimeStampedModel):
    asset_tag = models.CharField("patrimônio", max_length=50, unique=True)
    name = models.CharField("nome", max_length=150)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="assets",
        verbose_name="categoria",
    )
    sector = models.ForeignKey(
        Sector,
        on_delete=models.PROTECT,
        related_name="assets",
        verbose_name="setor",
    )
    status = models.ForeignKey(
        AssetStatus,
        on_delete=models.PROTECT,
        related_name="assets",
        verbose_name="status",
    )
    serial_number = models.CharField(
        "número de série",
        max_length=100,
        unique=True,
        null=True,
        blank=True,
    )
    manufacturer = models.CharField("fabricante", max_length=100, blank=True)
    model = models.CharField("modelo", max_length=100, blank=True)
    acquisition_date = models.DateField("data de aquisição", null=True, blank=True)
    purchase_value = models.DecimalField(
        "valor de compra",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    notes = models.TextField("observações", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_assets",
        null=True,
        editable=False,
        verbose_name="criado por",
    )

    class Meta:
        ordering = ("asset_tag",)
        verbose_name = "ativo"
        verbose_name_plural = "ativos"

    def __str__(self):
        return f"{self.asset_tag} - {self.name}"
