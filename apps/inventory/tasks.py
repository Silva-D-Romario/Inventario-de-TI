from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.inventory.models import Loan, Notification, Warranty


def _alert_recipients():
    return (
        User.objects.filter(is_active=True)
        .exclude(email="")
        .filter(Q(is_superuser=True) | Q(role__in=(User.Role.ADMIN, User.Role.TECHNICIAN)))
    )


def _create_alerts(*, recipients, alert_type, title, message, resource, dedup_key):
    created_count = 0
    for recipient in recipients:
        notification, created = Notification.objects.get_or_create(
            recipient=recipient,
            dedup_key=dedup_key,
            defaults={
                "alert_type": alert_type,
                "title": title,
                "message": message,
                "resource_type": resource._meta.label_lower,
                "resource_id": str(resource.pk),
            },
        )
        if not created:
            continue
        created_count += 1
        send_mail(
            subject=f"[Inventário de TI] {notification.title}",
            message=notification.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
            fail_silently=True,
        )
    return created_count


@shared_task(name="inventory.generate_alerts")
def generate_inventory_alerts():
    today = timezone.localdate()
    recipients = list(_alert_recipients())
    created_count = 0

    overdue_loans = Loan.objects.filter(
        returned_at__isnull=True,
        expected_return_date__lt=today,
    ).select_related("asset", "borrower")
    for loan in overdue_loans:
        title = f"Empréstimo vencido: {loan.asset.asset_tag}"
        message = (
            f"O ativo {loan.asset.asset_tag} - {loan.asset.name}, emprestado para "
            f"{loan.borrower.name}, deveria ter sido devolvido em "
            f"{loan.expected_return_date.strftime('%d/%m/%Y')}."
        )
        created_count += _create_alerts(
            recipients=recipients,
            alert_type=Notification.Type.OVERDUE_LOAN,
            title=title,
            message=message,
            resource=loan,
            dedup_key=f"overdue-loan:{loan.pk}:{loan.expected_return_date.isoformat()}",
        )

    warranty_limit = today + timedelta(days=settings.INVENTORY_WARRANTY_ALERT_DAYS)
    expiring_warranties = Warranty.objects.filter(
        start_date__lte=today,
        end_date__gte=today,
        end_date__lte=warranty_limit,
    ).select_related("asset")
    for warranty in expiring_warranties:
        title = f"Garantia próxima do fim: {warranty.asset.asset_tag}"
        message = (
            f"A garantia do ativo {warranty.asset.asset_tag} - {warranty.asset.name}, "
            f"fornecida por {warranty.provider}, termina em "
            f"{warranty.end_date.strftime('%d/%m/%Y')}."
        )
        created_count += _create_alerts(
            recipients=recipients,
            alert_type=Notification.Type.WARRANTY_EXPIRING,
            title=title,
            message=message,
            resource=warranty,
            dedup_key=f"warranty-expiring:{warranty.pk}:{warranty.end_date.isoformat()}",
        )

    return {
        "created": created_count,
        "overdue_loans": overdue_loans.count(),
        "expiring_warranties": expiring_warranties.count(),
        "recipients": len(recipients),
    }
