from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.inventory.models import AssetAttachment


@receiver(post_delete, sender=AssetAttachment)
def delete_attachment_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)
