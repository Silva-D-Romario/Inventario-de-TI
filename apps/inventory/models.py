import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


def validate_attachment_size(uploaded_file):
    max_size = 10 * 1024 * 1024
    if uploaded_file.size > max_size:
        raise ValidationError("O arquivo deve ter no máximo 10 MB.")


def asset_attachment_path(instance, filename):
    return f"inventory/assets/{instance.asset_id}/{filename}"


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
    public_id = models.UUIDField(
        "identificador público",
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
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


class Maintenance(TimeStampedModel):
    class Type(models.TextChoices):
        PREVENTIVE = "PREVENTIVE", "Preventiva"
        CORRECTIVE = "CORRECTIVE", "Corretiva"

    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "Em andamento"
        COMPLETED = "COMPLETED", "Concluída"
        CANCELLED = "CANCELLED", "Cancelada"

    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="maintenances",
        verbose_name="ativo",
    )
    maintenance_type = models.CharField(
        "tipo",
        max_length=20,
        choices=Type.choices,
    )
    status = models.CharField(
        "status",
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )
    description = models.TextField("descrição")
    provider = models.CharField("prestador", max_length=150, blank=True)
    started_at = models.DateField("iniciada em", default=timezone.localdate)
    completed_at = models.DateField("concluída em", null=True, blank=True)
    cost = models.DecimalField(
        "custo",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    resolution_notes = models.TextField("observações da conclusão", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_maintenances",
        null=True,
        editable=False,
        verbose_name="criado por",
    )

    class Meta:
        ordering = ("-started_at", "-created_at")
        verbose_name = "manutenção"
        verbose_name_plural = "manutenções"
        constraints = [
            models.UniqueConstraint(
                fields=("asset",),
                condition=models.Q(status="IN_PROGRESS"),
                name="inventory_unique_active_maintenance_per_asset",
            )
        ]

    def __str__(self):
        return f"{self.asset.asset_tag} - {self.get_maintenance_type_display()}"

    @property
    def is_active(self):
        return self.status == self.Status.IN_PROGRESS


class Warranty(TimeStampedModel):
    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="warranties",
        verbose_name="ativo",
    )
    provider = models.CharField("fornecedor", max_length=150)
    contract_number = models.CharField("contrato", max_length=100, blank=True)
    start_date = models.DateField("início")
    end_date = models.DateField("fim")
    coverage_notes = models.TextField("cobertura", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_warranties",
        null=True,
        editable=False,
        verbose_name="criado por",
    )

    class Meta:
        ordering = ("-end_date",)
        verbose_name = "garantia"
        verbose_name_plural = "garantias"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="inventory_warranty_end_on_or_after_start",
            )
        ]

    def __str__(self):
        return f"{self.asset.asset_tag} - {self.provider}"

    @property
    def is_active(self):
        today = timezone.localdate()
        return self.start_date <= today <= self.end_date


class AssetCost(TimeStampedModel):
    class Type(models.TextChoices):
        PURCHASE = "PURCHASE", "Compra"
        MAINTENANCE = "MAINTENANCE", "Manutenção"
        LICENSE = "LICENSE", "Licença"
        OTHER = "OTHER", "Outro"

    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="costs",
        verbose_name="ativo",
    )
    maintenance = models.ForeignKey(
        Maintenance,
        on_delete=models.PROTECT,
        related_name="cost_entries",
        null=True,
        blank=True,
        verbose_name="manutenção",
    )
    cost_type = models.CharField("tipo", max_length=20, choices=Type.choices)
    amount = models.DecimalField(
        "valor",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    occurred_on = models.DateField("data", default=timezone.localdate)
    description = models.TextField("descrição")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_asset_costs",
        null=True,
        editable=False,
        verbose_name="criado por",
    )

    class Meta:
        ordering = ("-occurred_on", "-created_at")
        verbose_name = "custo do ativo"
        verbose_name_plural = "custos dos ativos"

    def __str__(self):
        return f"{self.asset.asset_tag} - {self.amount}"


class AssetAttachment(TimeStampedModel):
    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="attachments",
        verbose_name="ativo",
    )
    maintenance = models.ForeignKey(
        Maintenance,
        on_delete=models.PROTECT,
        related_name="attachments",
        null=True,
        blank=True,
        verbose_name="manutenção",
    )
    file = models.FileField(
        "arquivo",
        upload_to=asset_attachment_path,
        validators=[
            FileExtensionValidator(("pdf", "png", "jpg", "jpeg", "webp")),
            validate_attachment_size,
        ],
    )
    description = models.CharField("descrição", max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="uploaded_asset_attachments",
        null=True,
        editable=False,
        verbose_name="enviado por",
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "anexo do ativo"
        verbose_name_plural = "anexos dos ativos"

    def __str__(self):
        return f"{self.asset.asset_tag} - {self.file.name}"


class AssetMovement(TimeStampedModel):
    class Type(models.TextChoices):
        LOAN = "LOAN", "Empréstimo"
        RETURN = "RETURN", "Devolução"
        TRANSFER = "TRANSFER", "Transferência"
        ASSIGNMENT = "ASSIGNMENT", "Atribuição"
        MAINTENANCE_START = "MAINTENANCE_START", "Início de manutenção"
        MAINTENANCE_END = "MAINTENANCE_END", "Fim de manutenção"

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
    maintenance = models.ForeignKey(
        Maintenance,
        on_delete=models.PROTECT,
        related_name="movements",
        null=True,
        blank=True,
        verbose_name="manutenção",
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


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "CREATE", "Criação"
        UPDATE = "UPDATE", "Alteração"
        DELETE = "DELETE", "Exclusão"
        ACTION = "ACTION", "Ação operacional"
        SCAN = "SCAN", "Leitura de QR Code"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="inventory_audit_logs",
        null=True,
        editable=False,
        verbose_name="usuário",
    )
    action = models.CharField("ação", max_length=10, choices=Action.choices)
    resource_type = models.CharField("tipo de recurso", max_length=100)
    object_id = models.CharField("identificador do objeto", max_length=64)
    object_repr = models.CharField("descrição do objeto", max_length=255)
    changes = models.JSONField("alterações", default=dict, blank=True)
    ip_address = models.GenericIPAddressField("endereço IP", null=True, blank=True)
    user_agent = models.TextField("agente do usuário", blank=True)
    path = models.CharField("rota", max_length=255, blank=True)
    method = models.CharField("método HTTP", max_length=10, blank=True)
    request_id = models.UUIDField("identificador da requisição", default=uuid.uuid4)
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "registro de auditoria"
        verbose_name_plural = "registros de auditoria"
        indexes = [
            models.Index(
                fields=("resource_type", "object_id"),
                name="inventory_audit_resource_idx",
            ),
            models.Index(fields=("actor", "created_at"), name="inventory_audit_actor_idx"),
        ]

    def __str__(self):
        return f"{self.get_action_display()} - {self.object_repr}"


class Notification(models.Model):
    class Type(models.TextChoices):
        OVERDUE_LOAN = "OVERDUE_LOAN", "Empréstimo vencido"
        WARRANTY_EXPIRING = "WARRANTY_EXPIRING", "Garantia próxima do fim"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="inventory_notifications",
        verbose_name="destinatário",
    )
    alert_type = models.CharField("tipo", max_length=30, choices=Type.choices)
    title = models.CharField("título", max_length=180)
    message = models.TextField("mensagem")
    resource_type = models.CharField("tipo de recurso", max_length=100)
    resource_id = models.CharField("identificador do recurso", max_length=64)
    dedup_key = models.CharField("chave de deduplicação", max_length=180)
    read_at = models.DateTimeField("lida em", null=True, blank=True)
    created_at = models.DateTimeField("criada em", auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "notificação"
        verbose_name_plural = "notificações"
        constraints = [
            models.UniqueConstraint(
                fields=("recipient", "dedup_key"),
                name="inv_notif_recip_dedup_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=("recipient", "read_at", "created_at"),
                name="inventory_notif_read_idx",
            )
        ]

    def __str__(self):
        return f"{self.recipient} - {self.title}"

    @property
    def is_read(self):
        return self.read_at is not None
