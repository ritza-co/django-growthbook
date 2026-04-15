from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from decimal import Decimal


class Command(BaseCommand):
    help = 'Seed database with sample data for the retail dashboard'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        with transaction.atomic():
            self._create_users()
            self._create_categories()
            self._create_products()
            self._create_orders()

        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))

    def _create_users(self):
        from apps.accounts.models import Profile

        users_data = [
            {'username': 'admin_user', 'email': 'admin@retail.com', 'role': 'admin',
             'first_name': 'Alice', 'last_name': 'Admin'},
            {'username': 'manager_user', 'email': 'manager@retail.com', 'role': 'manager',
             'first_name': 'Bob', 'last_name': 'Manager'},
            {'username': 'analyst_user', 'email': 'analyst@retail.com', 'role': 'analyst',
             'first_name': 'Carol', 'last_name': 'Analyst'},
            {'username': 'staff_user', 'email': 'staff@retail.com', 'role': 'staff',
             'first_name': 'Dave', 'last_name': 'Staff'},
        ]

        for data in users_data:
            role = data.pop('role')
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={**data, 'is_active': True}
            )
            if created:
                user.set_password('password123')
                user.save()
                profile, _ = Profile.objects.get_or_create(user=user)
                profile.role = role
                profile.phone = '+1-555-0100'
                profile.save()
                self.stdout.write(f'  Created user: {user.username} ({role})')
            else:
                # Still update role
                profile, _ = Profile.objects.get_or_create(user=user)
                profile.role = role
                profile.save()
                self.stdout.write(f'  User already exists: {user.username}')

    def _create_categories(self):
        from apps.inventory.models import Category

        categories_data = [
            {'name': 'Electronics', 'slug': 'electronics'},
            {'name': 'Audio', 'slug': 'audio'},
            {'name': 'Accessories', 'slug': 'accessories'},
            {'name': 'Cameras', 'slug': 'cameras'},
            {'name': 'Wearables', 'slug': 'wearables'},
        ]

        for data in categories_data:
            cat, created = Category.objects.get_or_create(slug=data['slug'], defaults=data)
            if created:
                self.stdout.write(f'  Created category: {cat.name}')

        self.categories = {c.slug: c for c in Category.objects.all()}

    def _create_products(self):
        from apps.inventory.models import Product

        products_data = [
            {
                'name': 'Samsung 65" 4K Smart TV',
                'sku': 'SMSTV65-4K',
                'description': 'Premium 4K UHD Smart TV with HDR and built-in streaming apps.',
                'category_slug': 'electronics',
                'price': Decimal('899.99'),
                'cost_price': Decimal('550.00'),
                'stock_quantity': 25,
                'reorder_threshold': 5,
            },
            {
                'name': 'Apple MacBook Pro 14"',
                'sku': 'APLMBP14-M3',
                'description': 'Apple MacBook Pro with M3 chip, 16GB RAM, 512GB SSD.',
                'category_slug': 'electronics',
                'price': Decimal('1999.99'),
                'cost_price': Decimal('1400.00'),
                'stock_quantity': 12,
                'reorder_threshold': 3,
            },
            {
                'name': 'Sony WH-1000XM5 Headphones',
                'sku': 'SNYWH1000XM5',
                'description': 'Industry-leading noise cancelling wireless headphones.',
                'category_slug': 'audio',
                'price': Decimal('349.99'),
                'cost_price': Decimal('200.00'),
                'stock_quantity': 40,
                'reorder_threshold': 10,
            },
            {
                'name': 'Bose SoundLink Flex Speaker',
                'sku': 'BSSLF-BLK',
                'description': 'Portable Bluetooth speaker, waterproof and dustproof.',
                'category_slug': 'audio',
                'price': Decimal('149.99'),
                'cost_price': Decimal('80.00'),
                'stock_quantity': 8,
                'reorder_threshold': 10,
            },
            {
                'name': 'USB-C Hub 7-in-1',
                'sku': 'USBCHUB-7IN1',
                'description': '7-in-1 USB-C hub with HDMI, USB 3.0, SD card reader.',
                'category_slug': 'accessories',
                'price': Decimal('49.99'),
                'cost_price': Decimal('20.00'),
                'stock_quantity': 3,
                'reorder_threshold': 15,
            },
            {
                'name': 'Logitech MX Master 3 Mouse',
                'sku': 'LGTMXM3-BLK',
                'description': 'Advanced wireless mouse for power users.',
                'category_slug': 'accessories',
                'price': Decimal('99.99'),
                'cost_price': Decimal('55.00'),
                'stock_quantity': 30,
                'reorder_threshold': 8,
            },
            {
                'name': 'Canon EOS R50 Mirrorless Camera',
                'sku': 'CNNEOSR50',
                'description': 'Compact mirrorless camera with 24.2 MP APS-C sensor.',
                'category_slug': 'cameras',
                'price': Decimal('679.99'),
                'cost_price': Decimal('420.00'),
                'stock_quantity': 7,
                'reorder_threshold': 5,
            },
            {
                'name': 'GoPro HERO12 Black',
                'sku': 'GPROH12-BLK',
                'description': 'Action camera with 5.3K video and HyperSmooth 6.0.',
                'category_slug': 'cameras',
                'price': Decimal('399.99'),
                'cost_price': Decimal('250.00'),
                'stock_quantity': 0,
                'reorder_threshold': 5,
            },
            {
                'name': 'Apple Watch Series 9',
                'sku': 'APLWS9-45BLK',
                'description': 'Apple Watch Series 9, 45mm, Midnight Aluminum.',
                'category_slug': 'wearables',
                'price': Decimal('429.99'),
                'cost_price': Decimal('280.00'),
                'stock_quantity': 18,
                'reorder_threshold': 5,
            },
            {
                'name': 'Fitbit Charge 6',
                'sku': 'FBTCH6-BLK',
                'description': 'Fitness tracker with built-in GPS and heart rate monitoring.',
                'category_slug': 'wearables',
                'price': Decimal('159.99'),
                'cost_price': Decimal('90.00'),
                'stock_quantity': 22,
                'reorder_threshold': 8,
            },
            {
                'name': 'Mechanical Keyboard TKL',
                'sku': 'MCHKBD-TKL-BLU',
                'description': 'Tenkeyless mechanical keyboard with blue switches and RGB.',
                'category_slug': 'accessories',
                'price': Decimal('89.99'),
                'cost_price': Decimal('45.00'),
                'stock_quantity': 5,
                'reorder_threshold': 8,
            },
            {
                'name': 'Dell 27" Monitor S2722D',
                'sku': 'DLLS2722D',
                'description': '27-inch QHD IPS monitor with USB-C connectivity.',
                'category_slug': 'electronics',
                'price': Decimal('329.99'),
                'cost_price': Decimal('200.00'),
                'stock_quantity': 14,
                'reorder_threshold': 4,
            },
        ]

        self.products = {}
        for data in products_data:
            category_slug = data.pop('category_slug')
            category = self.categories.get(category_slug)
            product, created = Product.objects.get_or_create(
                sku=data['sku'],
                defaults={**data, 'category': category, 'is_active': True}
            )
            self.products[product.sku] = product
            if created:
                self.stdout.write(f'  Created product: {product.name}')

    def _create_orders(self):
        from apps.orders.models import Order, OrderItem

        admin_user = User.objects.filter(username='admin_user').first()
        manager_user = User.objects.filter(username='manager_user').first()
        staff_user = User.objects.filter(username='staff_user').first()

        products = list(self.products.values())

        orders_data = [
            {
                'customer_name': 'John Smith',
                'customer_email': 'john.smith@example.com',
                'customer_phone': '+1-555-0201',
                'status': 'delivered',
                'created_by': admin_user,
                'items': [
                    {'product': products[0], 'quantity': 1, 'unit_price': products[0].price},
                    {'product': products[5], 'quantity': 1, 'unit_price': products[5].price},
                ],
            },
            {
                'customer_name': 'Sarah Johnson',
                'customer_email': 'sarah.j@example.com',
                'customer_phone': '+1-555-0202',
                'status': 'shipped',
                'created_by': manager_user,
                'items': [
                    {'product': products[1], 'quantity': 1, 'unit_price': products[1].price},
                ],
            },
            {
                'customer_name': 'Michael Brown',
                'customer_email': 'mbrown@example.com',
                'customer_phone': '+1-555-0203',
                'status': 'processing',
                'created_by': staff_user,
                'items': [
                    {'product': products[2], 'quantity': 2, 'unit_price': products[2].price},
                    {'product': products[3], 'quantity': 1, 'unit_price': products[3].price},
                ],
            },
            {
                'customer_name': 'Emily Davis',
                'customer_email': 'emily.d@example.com',
                'customer_phone': '+1-555-0204',
                'status': 'confirmed',
                'created_by': admin_user,
                'items': [
                    {'product': products[6], 'quantity': 1, 'unit_price': products[6].price},
                    {'product': products[4], 'quantity': 2, 'unit_price': products[4].price},
                ],
            },
            {
                'customer_name': 'Robert Wilson',
                'customer_email': 'rwilson@example.com',
                'customer_phone': '+1-555-0205',
                'status': 'pending',
                'created_by': staff_user,
                'items': [
                    {'product': products[8], 'quantity': 1, 'unit_price': products[8].price},
                ],
            },
            {
                'customer_name': 'Jessica Martinez',
                'customer_email': 'jmartinez@example.com',
                'customer_phone': '+1-555-0206',
                'status': 'cancelled',
                'created_by': manager_user,
                'items': [
                    {'product': products[9], 'quantity': 3, 'unit_price': products[9].price},
                    {'product': products[10], 'quantity': 1, 'unit_price': products[10].price},
                ],
            },
            {
                'customer_name': 'Chris Taylor',
                'customer_email': 'ctaylor@example.com',
                'customer_phone': '+1-555-0207',
                'status': 'delivered',
                'created_by': admin_user,
                'items': [
                    {'product': products[11], 'quantity': 2, 'unit_price': products[11].price},
                    {'product': products[5], 'quantity': 2, 'unit_price': products[5].price},
                ],
            },
            {
                'customer_name': 'Amanda Anderson',
                'customer_email': 'aanderson@example.com',
                'customer_phone': '+1-555-0208',
                'status': 'processing',
                'created_by': staff_user,
                'items': [
                    {'product': products[0], 'quantity': 1, 'unit_price': products[0].price},
                    {'product': products[2], 'quantity': 1, 'unit_price': products[2].price},
                ],
            },
        ]

        from django.db.models.signals import post_save
        from apps.orders.signals import update_order_total_on_item_save
        from apps.inventory.signals import update_product_stock_on_movement

        # Disconnect signals during seed to avoid double-counting stock
        post_save.disconnect(update_order_total_on_item_save, sender=OrderItem)
        post_save.disconnect(update_product_stock_on_movement)

        try:
            for data in orders_data:
                items_data = data.pop('items')
                order = Order.objects.create(**data)

                for item_data in items_data:
                    OrderItem.objects.create(
                        order=order,
                        product=item_data['product'],
                        quantity=item_data['quantity'],
                        unit_price=item_data['unit_price'],
                    )

                # Manually compute total
                total = sum(i.unit_price * i.quantity for i in order.items.all())
                Order.objects.filter(pk=order.pk).update(total_amount=total)
                self.stdout.write(f'  Created order: {order.order_number} ({order.status})')
        finally:
            # Reconnect signals
            post_save.connect(update_order_total_on_item_save, sender=OrderItem)
            from apps.inventory.models import StockMovement
            post_save.connect(update_product_stock_on_movement, sender=StockMovement)
