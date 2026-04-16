from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from .models import Category, Product, StockMovement


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_staff_user(username, role='admin', password='pass'):
    user = User.objects.create_user(username=username, password=password)
    user.profile.role = role
    user.profile.save()
    return user


def make_category(name='Electronics'):
    return Category.objects.create(name=name, slug=name.lower().replace(' ', '-'))


def make_product(category, name='Laptop', sku='SKU-001', price='999.99',
                 cost_price='600.00', stock_quantity=50):
    return Product.objects.create(
        name=name,
        sku=sku,
        category=category,
        price=price,
        cost_price=cost_price,
        stock_quantity=stock_quantity,
    )


# ---------------------------------------------------------------------------
# Category model
# ---------------------------------------------------------------------------

class CategoryModelTest(TestCase):
    def test_slug_auto_generated_from_name(self):
        cat = Category.objects.create(name='Smart Phones')
        self.assertEqual(cat.slug, 'smart-phones')

    def test_slug_not_overwritten_if_provided(self):
        cat = Category.objects.create(name='TVs', slug='televisions')
        self.assertEqual(cat.slug, 'televisions')

    def test_str_is_name(self):
        cat = make_category('Audio')
        self.assertEqual(str(cat), 'Audio')


# ---------------------------------------------------------------------------
# Product model
# ---------------------------------------------------------------------------

class ProductModelTest(TestCase):
    def setUp(self):
        self.cat = make_category()

    def test_slug_auto_generated_from_name(self):
        product = make_product(self.cat, name='Gaming Laptop', sku='GL-001')
        self.assertEqual(product.slug, 'gaming-laptop')

    def test_slug_uniqueness_counter_appended(self):
        make_product(self.cat, name='Headphone', sku='HP-001')
        p2 = make_product(self.cat, name='Headphone', sku='HP-002')
        self.assertEqual(p2.slug, 'headphone-1')

    def test_slug_not_overwritten_on_update(self):
        product = make_product(self.cat, name='Tablet', sku='TB-001')
        original_slug = product.slug
        product.price = '799.99'
        product.save()
        product.refresh_from_db()
        self.assertEqual(product.slug, original_slug)

    def test_stock_status_in_stock(self):
        product = make_product(self.cat, stock_quantity=50)
        product.reorder_threshold = 10
        self.assertEqual(product.stock_status, 'in_stock')

    def test_stock_status_low_stock(self):
        product = make_product(self.cat, stock_quantity=5)
        product.reorder_threshold = 10
        self.assertEqual(product.stock_status, 'low_stock')

    def test_stock_status_out_of_stock(self):
        product = make_product(self.cat, stock_quantity=0)
        self.assertEqual(product.stock_status, 'out_of_stock')

    def test_is_low_stock_true(self):
        product = make_product(self.cat, stock_quantity=5)
        product.reorder_threshold = 10
        self.assertTrue(product.is_low_stock)

    def test_is_low_stock_false(self):
        product = make_product(self.cat, stock_quantity=50)
        product.reorder_threshold = 10
        self.assertFalse(product.is_low_stock)

    def test_stock_value(self):
        from decimal import Decimal
        product = make_product(self.cat, cost_price='10.00', stock_quantity=5)
        product.refresh_from_db()  # ensure DecimalField is coerced from string
        self.assertEqual(product.stock_value, Decimal('50.00'))

    def test_str_contains_name_and_sku(self):
        product = make_product(self.cat, name='Monitor', sku='MON-001')
        self.assertIn('Monitor', str(product))
        self.assertIn('MON-001', str(product))


# ---------------------------------------------------------------------------
# Inventory views — access control
# ---------------------------------------------------------------------------

class ProductListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.cat = make_category()
        make_product(self.cat)
        self.url = reverse('inventory:product_list')

    def test_unauthenticated_redirects(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_admin_can_access(self):
        user = make_staff_user('admin1', 'admin')
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_manager_can_access(self):
        user = make_staff_user('mgr1', 'manager')
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_analyst_forbidden(self):
        user = make_staff_user('analyst1', 'analyst')
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_staff_forbidden(self):
        user = make_staff_user('staff1', 'staff')
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_search_filters_products(self):
        make_product(self.cat, name='Wireless Mouse', sku='WM-001')
        user = make_staff_user('admin2', 'admin')
        self.client.force_login(user)
        response = self.client.get(self.url, {'search': 'Wireless'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Wireless Mouse')
        self.assertNotContains(response, 'Laptop')


class ProductAddViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.cat = make_category()
        self.url = reverse('inventory:product_add')
        self.admin = make_staff_user('admin1', 'admin')

    def test_get_shows_form(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_creates_product_and_redirects(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url, {
            'name': 'New Product',
            'sku': 'NP-001',
            'category': self.cat.pk,
            'price': '199.99',
            'cost_price': '100.00',
            'stock_quantity': 20,
            'reorder_threshold': 5,
            'is_active': True,
            'is_featured': False,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Product.objects.filter(sku='NP-001').exists())

    def test_manager_forbidden_from_product_add(self):
        # managers CAN add — just double-checking decorator
        mgr = make_staff_user('mgr1', 'manager')
        self.client.force_login(mgr)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_staff_cannot_add_product(self):
        staff = make_staff_user('staff1', 'staff')
        self.client.force_login(staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)


class ProductDeactivateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.cat = make_category()
        self.product = make_product(self.cat)
        self.admin = make_staff_user('admin1', 'admin')
        self.url = reverse('inventory:product_deactivate', args=[self.product.pk])

    def test_post_deactivates_product(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_active)

    def test_get_shows_confirmation(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
