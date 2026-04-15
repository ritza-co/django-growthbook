from django.db import models
from django.contrib.auth.models import User
from apps.inventory.models import Product


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    order_number = models.CharField(max_length=20, unique=True, blank=True)
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            super().save(*args, **kwargs)
            self.order_number = f'ORD-{self.pk:05d}'
            Order.objects.filter(pk=self.pk).update(order_number=self.order_number)
        else:
            super().save(*args, **kwargs)

    def compute_total(self):
        total = sum(item.line_total for item in self.items.all())
        self.total_amount = total
        Order.objects.filter(pk=self.pk).update(total_amount=total)
        return total

    @property
    def status_color(self):
        colors = {
            'pending': 'yellow',
            'confirmed': 'blue',
            'processing': 'indigo',
            'shipped': 'purple',
            'delivered': 'green',
            'cancelled': 'red',
        }
        return colors.get(self.status, 'gray')

    @property
    def next_statuses(self):
        """Returns the allowed next statuses for forward movement."""
        flow = {
            'pending': ['confirmed'],
            'confirmed': ['processing'],
            'processing': ['shipped'],
            'shipped': ['delivered'],
            'delivered': [],
            'cancelled': [],
        }
        return flow.get(self.status, [])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.product.name} in {self.order.order_number}"

    @property
    def line_total(self):
        return self.quantity * self.unit_price
