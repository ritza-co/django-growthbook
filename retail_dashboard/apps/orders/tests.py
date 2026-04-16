from decimal import Decimal

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from apps.inventory.models import Category, Product
from .models import Order, OrderItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_staff_user(username, role='admin', password='pass'):
    user = User.objects.create_user(username=username, password=password)
    user.profile.role = role
    user.profile.save()
    return user


def make_product(name='Laptop', sku='SKU-001', price='999.99', cost_price='600.00',
                 stock_quantity=50):
    cat, _ = Category.objects.get_or_create(name='Electronics', defaults={'slug': 'electronics'})
    return Product.objects.create(
        name=name, sku=sku, category=cat,
        price=price, cost_price=cost_price, stock_quantity=stock_quantity,
    )


def make_order(status='pending', source='internal', created_by=None):
    order = Order.objects.create(
        customer_name='Test Customer',
        customer_email='customer@example.com',
        status=status,
        source=source,
        created_by=created_by,
    )
    return order


# ---------------------------------------------------------------------------
# Order model
# ---------------------------------------------------------------------------

class OrderModelTest(TestCase):
    def test_order_number_auto_assigned(self):
        order = make_order()
        self.assertTrue(order.order_number.startswith('ORD-'))

    def test_order_number_zero_padded(self):
        order = make_order()
        self.assertRegex(order.order_number, r'^ORD-\d{5}$')

    def test_order_number_not_overwritten_on_update(self):
        order = make_order()
        original = order.order_number
        order.status = 'confirmed'
        order.save()
        order.refresh_from_db()
        self.assertEqual(order.order_number, original)

    def test_compute_total_sums_line_totals(self):
        product = make_product()
        order = make_order()
        OrderItem.objects.create(order=order, product=product, quantity=2, unit_price=Decimal('100.00'))
        OrderItem.objects.create(order=order, product=product, quantity=1, unit_price=Decimal('50.00'))
        total = order.compute_total()
        self.assertEqual(total, Decimal('250.00'))
        order.refresh_from_db()
        self.assertEqual(order.total_amount, Decimal('250.00'))

    def test_status_color_maps_correctly(self):
        order = make_order(status='pending')
        self.assertEqual(order.status_color, 'yellow')
        order.status = 'delivered'
        self.assertEqual(order.status_color, 'green')
        order.status = 'cancelled'
        self.assertEqual(order.status_color, 'red')

    def test_next_statuses_flow(self):
        order = make_order(status='pending')
        self.assertEqual(order.next_statuses, ['confirmed'])
        order.status = 'shipped'
        self.assertEqual(order.next_statuses, ['delivered'])
        order.status = 'delivered'
        self.assertEqual(order.next_statuses, [])

    def test_cancelled_has_no_next_statuses(self):
        order = make_order(status='cancelled')
        self.assertEqual(order.next_statuses, [])

    def test_str_is_order_number(self):
        order = make_order()
        self.assertEqual(str(order), order.order_number)


# ---------------------------------------------------------------------------
# OrderItem model
# ---------------------------------------------------------------------------

class OrderItemModelTest(TestCase):
    def test_line_total_is_quantity_times_unit_price(self):
        product = make_product()
        order = make_order()
        item = OrderItem.objects.create(
            order=order, product=product, quantity=3, unit_price=Decimal('25.00')
        )
        self.assertEqual(item.line_total, Decimal('75.00'))

    def test_str_contains_quantity_and_product_name(self):
        product = make_product(name='Monitor')
        order = make_order()
        item = OrderItem.objects.create(
            order=order, product=product, quantity=2, unit_price=Decimal('300.00')
        )
        self.assertIn('2', str(item))
        self.assertIn('Monitor', str(item))


# ---------------------------------------------------------------------------
# Order list view — access control
# ---------------------------------------------------------------------------

class OrderListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('orders:order_list')

    def test_unauthenticated_redirects(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_admin_can_access(self):
        self.client.force_login(make_staff_user('admin1', 'admin'))
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_manager_can_access(self):
        self.client.force_login(make_staff_user('mgr1', 'manager'))
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_staff_can_access(self):
        self.client.force_login(make_staff_user('staff1', 'staff'))
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_analyst_forbidden(self):
        self.client.force_login(make_staff_user('analyst1', 'analyst'))
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_status_filter(self):
        make_order(status='pending')
        make_order(status='shipped')
        self.client.force_login(make_staff_user('admin2', 'admin'))
        response = self.client.get(self.url, {'status': 'shipped'})
        self.assertEqual(response.status_code, 200)
        # Only the shipped order's badge should appear
        self.assertContains(response, 'Shipped')

    def test_search_filter(self):
        make_order()
        self.client.force_login(make_staff_user('admin3', 'admin'))
        response = self.client.get(self.url, {'search': 'Test Customer'})
        self.assertContains(response, 'Test Customer')


# ---------------------------------------------------------------------------
# Order detail view
# ---------------------------------------------------------------------------

class OrderDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.order = make_order()
        self.url = reverse('orders:order_detail', args=[self.order.pk])

    def test_admin_can_view(self):
        self.client.force_login(make_staff_user('admin1', 'admin'))
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_shows_order_number(self):
        self.client.force_login(make_staff_user('admin2', 'admin'))
        response = self.client.get(self.url)
        self.assertContains(response, self.order.order_number)

    def test_analyst_forbidden(self):
        self.client.force_login(make_staff_user('analyst1', 'analyst'))
        self.assertEqual(self.client.get(self.url).status_code, 403)


# ---------------------------------------------------------------------------
# Order status update view
# ---------------------------------------------------------------------------

class OrderUpdateStatusTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.order = make_order(status='pending')
        self.url = reverse('orders:order_update_status', args=[self.order.pk])

    def test_admin_can_set_any_status(self):
        self.client.force_login(make_staff_user('admin1', 'admin'))
        response = self.client.post(self.url, {'status': 'shipped'})
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'shipped')

    def test_staff_can_only_advance_to_next_status(self):
        self.client.force_login(make_staff_user('staff1', 'staff'))
        # pending → confirmed is valid
        response = self.client.post(self.url, {'status': 'confirmed'})
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'confirmed')

    def test_staff_cannot_skip_status(self):
        self.client.force_login(make_staff_user('staff2', 'staff'))
        # pending → shipped is invalid for staff
        response = self.client.post(self.url, {'status': 'shipped'})
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        # Status should NOT have changed
        self.assertEqual(self.order.status, 'pending')

    def test_analyst_forbidden(self):
        self.client.force_login(make_staff_user('analyst1', 'analyst'))
        self.assertEqual(self.client.post(self.url, {'status': 'confirmed'}).status_code, 403)


# ---------------------------------------------------------------------------
# Order CSV export
# ---------------------------------------------------------------------------

class OrderExportCSVTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('orders:order_export_csv')
        make_order()

    def test_admin_gets_csv(self):
        self.client.force_login(make_staff_user('admin1', 'admin'))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_staff_forbidden(self):
        self.client.force_login(make_staff_user('staff1', 'staff'))
        self.assertEqual(self.client.get(self.url).status_code, 403)
