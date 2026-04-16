from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import OrderItem
from apps.inventory.models import StockMovement


@receiver(post_save, sender=OrderItem)
def update_order_total_on_item_save(sender, instance, created, **kwargs):
    instance.order.compute_total()

    if created:
        # Create a StockMovement for the sale
        StockMovement.objects.create(
            product=instance.product,
            movement_type='sale',
            quantity_change=-instance.quantity,
            note=f'Sale via order {instance.order.order_number}',
            created_by=instance.order.created_by,
        )


@receiver(post_delete, sender=OrderItem)
def update_order_total_on_item_delete(sender, instance, **kwargs):
    try:
        instance.order.compute_total()
    except Exception:
        pass
