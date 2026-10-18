from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


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


class ResponsiblePerson(TimeStampedModel):
    name = models.CharField("nome", max_length=150)
    email = models.EmailField("e-mail", unique=True)
    employee_id = models.CharField(
        "matrícula",
        max_length=50,
        unique=True,
        null=True,
        blank=True,
    )
    phone = models.CharField("telefone", max_length=30, blank=True)
    sector = models.ForeignKey(
        Sector,
        on_delete=models.PROTECT,
        related_name="responsible_people",
        verbose_name="setor",
    )
    is_active = models.BooleanField("ativo", default=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "responsável"
        verbose_name_plural = "responsáveis"

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
    responsible = models.ForeignKey(
        ResponsiblePerson,
        on_delete=models.PROTECT,
        related_name="assets",
        null=True,
        blank=True,
        verbose_name="responsável atual",
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


class Loan(TimeStampedModel):
    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="loans",
        verbose_name="ativo",
    )
    borrower = models.ForeignKey(
        ResponsiblePerson,
        on_delete=models.PROTECT,
        related_name="loans",
        verbose_name="responsável",
    )
    loaned_at = models.DateField("emprestado em", default=timezone.localdate)
    expected_return_date = models.DateField("devolução prevista")
    returned_at = models.DateField("devolvido em", null=True, blank=True)
    notes = models.TextField("observações", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_loans",
        null=True,
        editable=False,
        verbose_name="criado por",
    )

    class Meta:
        ordering = ("-loaned_at", "-created_at")
        verbose_name = "empréstimo"
        verbose_name_plural = "empréstimos"
        constraints = [
            models.UniqueConstraint(
                fields=("asset",),
                condition=models.Q(returned_at__isnull=True),
                name="inventory_unique_active_loan_per_asset",
            )
        ]

    def __str__(self):
        return f"{self.asset.asset_tag} - {self.borrower.name}"

    @property
    def is_active(self):
        return self.returned_at is None


class AssetMovement(TimeStampedModel):
    class Type(models.TextChoices):
        LOAN = "LOAN", "Empréstimo"
        RETURN = "RETURN", "Devolução"
        TRANSFER = "TRANSFER", "Transferência"
        ASSIGNMENT = "ASSIGNMENT", "Atribuição"

    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="movements",
        verbose_name="ativo",
    )
    movement_type = models.CharField("tipo", max_length=20, choices=Type.choices)
    from_sector = models.ForeignKey(
        Sector,
        on_delete=models.PROTECT,
        related_name="outgoing_movements",
        null=True,
        blank=True,
        verbose_name="setor de origem",
    )
    to_sector = models.ForeignKey(
        Sector,
        on_delete=models.PROTECT,
        related_name="incoming_movements",
        null=True,
        blank=True,
        verbose_name="setor de destino",
    )
    responsible = models.ForeignKey(
        ResponsiblePerson,
        on_delete=models.PROTECT,
        related_name="movements",
        null=True,
        blank=True,
        verbose_name="responsável",
    )
    loan = models.ForeignKey(
        Loan,
        on_delete=models.PROTECT,
        related_name="movements",
        null=True,
        blank=True,
        verbose_name="empréstimo",
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="asset_movements",
        null=True,
        editable=False,
        verbose_name="realizado por",
    )
    notes = models.TextField("observações", blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "movimentação de ativo"
        verbose_name_plural = "movimentações de ativos"

    def __str__(self):
        return f"{self.asset.asset_tag} - {self.get_movement_type_display()}"
