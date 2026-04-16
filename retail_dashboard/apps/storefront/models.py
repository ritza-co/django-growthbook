from django.db import models


class Review(models.Model):
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField()  # 1-5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'customer')
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.customer} on {self.product} ({self.rating}/5)"


class ProductImage(models.Model):
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/')
    is_primary = models.BooleanField(default=False)
    alt_text = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Image for {self.product.name}"
