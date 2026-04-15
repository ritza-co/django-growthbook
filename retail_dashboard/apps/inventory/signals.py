from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StockMovement


@receiver(post_save, sender=StockMovement)
def update_product_stock_on_movement(sender, instance, created, **kwargs):
    if created:
        product = instance.product
        product.stock_quantity += instance.quantity_change
        if product.stock_quantity < 0:
            product.stock_quantity = 0
        product.save(update_fields=['stock_quantity'])
