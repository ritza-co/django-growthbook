from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from apps.inventory.models import Category, Product
from apps.orders.models import Order, OrderItem
from apps.customers.models import Customer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_category(name='Electronics'):
    return Category.objects.get_or_create(
        name=name, defaults={'slug': name.lower().replace(' ', '-')}
    )[0]


def make_product(name='Laptop', sku='SKU-001', price='999.99', stock_quantity=50,
                 is_featured=False, is_active=True):
    cat = make_category()
    return Product.objects.create(
        name=name, sku=sku, category=cat,
        price=price, cost_price='500.00',
        stock_quantity=stock_quantity,
        is_featured=is_featured,
        is_active=is_active,
    )


def make_customer_user(username='cust', email='cust@example.com', password='pass'):
    user = User.objects.create_user(username=username, email=email, password=password)
    user.profile.delete()
    Customer.objects.create(user=user)
    return user


# ---------------------------------------------------------------------------
# Homepage
# ---------------------------------------------------------------------------

class HomepageTest(TestCase):
    def test_homepage_returns_200(self):
        response = self.client.get(reverse('storefront:home'))
        self.assertEqual(response.status_code, 200)

    def test_featured_products_in_context(self):
        p = make_product(name='Featured', sku='F-001', is_featured=True)
        response = self.client.get(reverse('storefront:home'))
        self.assertIn(p, response.context['featured_products'])

    def test_non_featured_products_not_shown(self):
        p = make_product(name='NotFeatured', sku='NF-001', is_featured=False)
        response = self.client.get(reverse('storefront:home'))
        self.assertNotIn(p, response.context['featured_products'])


# ---------------------------------------------------------------------------
# Product catalog
# ---------------------------------------------------------------------------

class ProductCatalogTest(TestCase):
    def setUp(self):
        self.url = reverse('storefront:catalog')
        self.p1 = make_product(name='Laptop', sku='LAP-001', price='999.99', stock_quantity=10)
        self.p2 = make_product(name='Phone', sku='PHN-001', price='499.99', stock_quantity=0)

    def test_catalog_returns_200(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_shows_active_products(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Laptop')
        self.assertContains(response, 'Phone')

    def test_in_stock_filter_excludes_out_of_stock(self):
        response = self.client.get(self.url, {'in_stock': '1'})
        self.assertContains(response, 'Laptop')
        self.assertNotContains(response, 'Phone')

    def test_price_max_filter(self):
        response = self.client.get(self.url, {'price_max': '600'})
        self.assertNotContains(response, 'Laptop')
        self.assertContains(response, 'Phone')

    def test_price_min_filter(self):
        response = self.client.get(self.url, {'price_min': '700'})
        self.assertContains(response, 'Laptop')
        self.assertNotContains(response, 'Phone')

    def test_inactive_products_not_shown(self):
        make_product(name='Inactive', sku='INA-001', is_active=False)
        response = self.client.get(self.url)
        self.assertNotContains(response, 'Inactive')


# ---------------------------------------------------------------------------
# Product detail
# ---------------------------------------------------------------------------

class ProductDetailTest(TestCase):
    def setUp(self):
        self.product = make_product(name='Monitor', sku='MON-001')
        self.url = reverse('storefront:product_detail', args=[self.product.slug])

    def test_returns_200(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_shows_product_name(self):
        self.assertContains(self.client.get(self.url), 'Monitor')

    def test_inactive_product_returns_404(self):
        inactive = make_product(name='Gone', sku='GON-001', is_active=False)
        url = reverse('storefront:product_detail', args=[inactive.slug])
        self.assertEqual(self.client.get(url).status_code, 404)


# ---------------------------------------------------------------------------
# Cart — add
# ---------------------------------------------------------------------------

class CartAddTest(TestCase):
    def setUp(self):
        self.product = make_product()
        self.url = reverse('storefront:cart_add', args=[self.product.pk])

    def test_add_to_cart_stores_in_session(self):
        self.client.post(self.url, {'quantity': 2})
        cart = self.client.session.get('cart', {})
        self.assertIn(str(self.product.pk), cart)
        self.assertEqual(cart[str(self.product.pk)]['quantity'], 2)

    def test_add_same_product_twice_increments_quantity(self):
        self.client.post(self.url, {'quantity': 1})
        self.client.post(self.url, {'quantity': 3})
        cart = self.client.session.get('cart', {})
        self.assertEqual(cart[str(self.product.pk)]['quantity'], 4)

    def test_add_redirects_to_cart(self):
        response = self.client.post(self.url, {'quantity': 1})
        self.assertRedirects(response, reverse('storefront:cart'))

    def test_htmx_request_returns_partial(self):
        response = self.client.post(
            self.url, {'quantity': 1}, HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'cart-count-badge')

    def test_get_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_inactive_product_returns_404(self):
        inactive = make_product(name='Old', sku='OLD-001', is_active=False)
        url = reverse('storefront:cart_add', args=[inactive.pk])
        response = self.client.post(url, {'quantity': 1})
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# Cart — update
# ---------------------------------------------------------------------------

class CartUpdateTest(TestCase):
    def setUp(self):
        self.product = make_product()
        self.url = reverse('storefront:cart_update')
        # Seed cart
        session = self.client.session
        session['cart'] = {str(self.product.pk): {'quantity': 3, 'unit_price': '999.99'}}
        session.save()

    def test_update_quantity(self):
        self.client.post(self.url, {'product_id': self.product.pk, 'quantity': 5})
        cart = self.client.session['cart']
        self.assertEqual(cart[str(self.product.pk)]['quantity'], 5)

    def test_quantity_zero_removes_item(self):
        self.client.post(self.url, {'product_id': self.product.pk, 'quantity': 0})
        cart = self.client.session['cart']
        self.assertNotIn(str(self.product.pk), cart)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)


# ---------------------------------------------------------------------------
# Cart — remove
# ---------------------------------------------------------------------------

class CartRemoveTest(TestCase):
    def setUp(self):
        self.product = make_product()
        self.url = reverse('storefront:cart_remove', args=[self.product.pk])
        session = self.client.session
        session['cart'] = {str(self.product.pk): {'quantity': 2, 'unit_price': '999.99'}}
        session.save()

    def test_removes_product_from_cart(self):
        self.client.post(self.url)
        cart = self.client.session.get('cart', {})
        self.assertNotIn(str(self.product.pk), cart)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)


# ---------------------------------------------------------------------------
# Cart view
# ---------------------------------------------------------------------------

class CartViewTest(TestCase):
    def test_empty_cart_returns_200(self):
        self.assertEqual(self.client.get(reverse('storefront:cart')).status_code, 200)

    def test_cart_shows_products(self):
        product = make_product(name='Keyboard', sku='KB-001', price='49.99')
        session = self.client.session
        session['cart'] = {str(product.pk): {'quantity': 1, 'unit_price': '49.99'}}
        session.save()
        response = self.client.get(reverse('storefront:cart'))
        self.assertContains(response, 'Keyboard')


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------

class CheckoutTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_customer_user(username='buyer', email='buyer@example.com')
        self.product = make_product(name='Headset', sku='HS-001', price='150.00', stock_quantity=10)
        self.url = reverse('storefront:checkout')

    def _seed_cart(self, quantity=1):
        session = self.client.session
        session['cart'] = {
            str(self.product.pk): {'quantity': quantity, 'unit_price': str(self.product.price)}
        }
        session.save()

    def test_unauthenticated_redirects_to_login(self):
        self._seed_cart()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_empty_cart_redirects_back(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('storefront:cart'))

    def test_get_shows_checkout_form(self):
        self.client.force_login(self.user)
        self._seed_cart()
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_post_creates_order(self):
        self.client.force_login(self.user)
        self._seed_cart(quantity=2)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        order = Order.objects.filter(customer_email=self.user.email).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.source, 'storefront')

    def test_checkout_creates_order_items(self):
        self.client.force_login(self.user)
        self._seed_cart(quantity=3)
        self.client.post(self.url)
        order = Order.objects.filter(customer_email=self.user.email).first()
        self.assertEqual(order.items.count(), 1)
        item = order.items.first()
        self.assertEqual(item.quantity, 3)

    def test_checkout_decrements_stock(self):
        self.client.force_login(self.user)
        self._seed_cart(quantity=4)
        self.client.post(self.url)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 6)

    def test_checkout_clears_cart(self):
        self.client.force_login(self.user)
        self._seed_cart()
        self.client.post(self.url)
        cart = self.client.session.get('cart', {})
        self.assertEqual(cart, {})

    def test_checkout_computes_total(self):
        self.client.force_login(self.user)
        self._seed_cart(quantity=2)
        self.client.post(self.url)
        order = Order.objects.filter(customer_email=self.user.email).first()
        self.assertEqual(order.total_amount, Decimal('300.00'))

    def test_insufficient_stock_shows_error(self):
        self.client.force_login(self.user)
        self._seed_cart(quantity=100)  # only 10 in stock
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Not enough stock')
        self.assertFalse(Order.objects.filter(customer_email=self.user.email).exists())


# ---------------------------------------------------------------------------
# Order confirm
# ---------------------------------------------------------------------------

class OrderConfirmTest(TestCase):
    def test_shows_order_details(self):
        order = Order.objects.create(
            customer_name='Jane', customer_email='jane@example.com', source='storefront'
        )
        url = reverse('storefront:order_confirm', args=[order.order_number])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, order.order_number)

    def test_status_steps_in_context(self):
        order = Order.objects.create(
            customer_name='Jane', customer_email='jane@example.com', source='storefront'
        )
        url = reverse('storefront:order_confirm', args=[order.order_number])
        response = self.client.get(url)
        self.assertIn('status_steps', response.context)
        self.assertEqual(len(response.context['status_steps']), 5)


# ---------------------------------------------------------------------------
# Order tracking
# ---------------------------------------------------------------------------

class TrackOrderTest(TestCase):
    def setUp(self):
        self.url = reverse('storefront:track_order')
        self.order = Order.objects.create(
            customer_name='Tracker', customer_email='tracker@example.com', source='storefront'
        )

    def test_get_returns_200(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_post_with_valid_order_number(self):
        response = self.client.post(self.url, {'order_number': self.order.order_number})
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['order'])
        self.assertEqual(response.context['order'].pk, self.order.pk)

    def test_post_with_invalid_order_number(self):
        response = self.client.post(self.url, {'order_number': 'ORD-99999'})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['order'])
        self.assertContains(response, 'No order found')

    def test_post_with_empty_order_number(self):
        response = self.client.post(self.url, {'order_number': ''})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter an order number')

    def test_status_steps_always_in_context(self):
        response = self.client.get(self.url)
        self.assertIn('status_steps', response.context)


# ---------------------------------------------------------------------------
# Review submission
# ---------------------------------------------------------------------------

class SubmitReviewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_customer_user(username='reviewer', email='rev@example.com')
        self.product = make_product(name='Speaker', sku='SPK-001')
        self.url = reverse('storefront:submit_review', args=[self.product.pk])

    def test_unauthenticated_redirects(self):
        response = self.client.post(self.url, {'rating': 4, 'comment': 'Great!'})
        self.assertEqual(response.status_code, 302)

    def test_customer_can_submit_review(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {'rating': 5, 'comment': 'Excellent!'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.product.reviews.count(), 1)

    def test_invalid_rating_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {'rating': 10, 'comment': 'Too high'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.product.reviews.count(), 0)

    def test_second_review_updates_existing(self):
        self.client.force_login(self.user)
        self.client.post(self.url, {'rating': 3, 'comment': 'OK'})
        self.client.post(self.url, {'rating': 5, 'comment': 'Changed mind!'})
        self.assertEqual(self.product.reviews.count(), 1)
        review = self.product.reviews.first()
        self.assertEqual(review.rating, 5)

    def test_get_not_allowed(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 405)
