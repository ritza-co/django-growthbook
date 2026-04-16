from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from apps.orders.models import Order
from apps.inventory.models import Category, Product
from .models import Customer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_customer_user(username='customer1', email='customer@example.com', password='pass'):
    user = User.objects.create_user(username=username, email=email, password=password)
    user.profile.delete()
    Customer.objects.create(user=user)
    return user


def make_staff_user(username='admin1', role='admin', password='pass'):
    user = User.objects.create_user(username=username, password=password)
    user.profile.role = role
    user.profile.save()
    return user


def make_order(email='customer@example.com', order_number=None):
    order = Order.objects.create(
        customer_name='Test Customer',
        customer_email=email,
        source='storefront',
    )
    return order


# ---------------------------------------------------------------------------
# Customer Registration
# ---------------------------------------------------------------------------

class CustomerRegisterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('customers:register')

    def test_get_shows_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_register_creates_user_and_customer(self):
        response = self.client.post(self.url, {
            'username': 'newcustomer',
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'Customer',
            'password1': 'SuperSecret99!',
            'password2': 'SuperSecret99!',
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='newcustomer')
        self.assertTrue(hasattr(user, 'customer'))

    def test_register_deletes_auto_created_profile(self):
        self.client.post(self.url, {
            'username': 'nocustomerprofile',
            'email': 'ncp@example.com',
            'first_name': 'No',
            'last_name': 'Profile',
            'password1': 'SuperSecret99!',
            'password2': 'SuperSecret99!',
        })
        user = User.objects.get(username='nocustomerprofile')
        self.assertFalse(hasattr(user, 'profile'))

    def test_register_logs_in_and_redirects_to_home(self):
        response = self.client.post(self.url, {
            'username': 'autologin',
            'email': 'autologin@example.com',
            'first_name': 'Auto',
            'last_name': 'Login',
            'password1': 'SuperSecret99!',
            'password2': 'SuperSecret99!',
        })
        self.assertRedirects(response, reverse('storefront:home'))
        # Session should show user is authenticated
        self.assertIn('_auth_user_id', self.client.session)

    def test_invalid_form_does_not_create_user(self):
        self.client.post(self.url, {
            'username': '',
            'email': 'bad',
            'password1': 'pass',
            'password2': 'mismatch',
        })
        self.assertFalse(User.objects.filter(email='bad').exists())


# ---------------------------------------------------------------------------
# Customer Login
# ---------------------------------------------------------------------------

class CustomerLoginTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('customers:login')

    def test_get_shows_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_customer_can_log_in(self):
        make_customer_user(username='cust1', email='cust1@example.com', password='testpass')
        response = self.client.post(self.url, {'username': 'cust1', 'password': 'testpass'})
        self.assertEqual(response.status_code, 302)

    def test_staff_blocked_from_customer_login(self):
        make_staff_user(username='staffonly', role='admin', password='testpass')
        response = self.client.post(self.url, {'username': 'staffonly', 'password': 'testpass'})
        self.assertEqual(response.status_code, 200)  # stays on login page
        self.assertContains(response, 'not a customer account')

    def test_wrong_password_rejected(self):
        make_customer_user(username='cust2', password='rightpass')
        response = self.client.post(self.url, {'username': 'cust2', 'password': 'wrongpass'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')

    def test_authenticated_customer_redirected_from_login(self):
        user = make_customer_user(username='cust3', password='pass')
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)


# ---------------------------------------------------------------------------
# Customer Logout
# ---------------------------------------------------------------------------

class CustomerLogoutTest(TestCase):
    def test_logout_redirects_to_login(self):
        user = make_customer_user()
        self.client = Client()
        self.client.force_login(user)
        response = self.client.get(reverse('customers:logout'))
        self.assertRedirects(response, reverse('customers:login'))
        self.assertNotIn('_auth_user_id', self.client.session)


# ---------------------------------------------------------------------------
# Account view
# ---------------------------------------------------------------------------

class CustomerAccountTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_customer_user(username='accuser', email='acc@example.com')
        self.url = reverse('customers:account')

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f'/store/login/?next={self.url}')

    def test_customer_can_view_account(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_account_update_saves_changes(self):
        self.client.force_login(self.user)
        self.client.post(self.url, {
            'first_name': 'Updated',
            'last_name': 'Name',
            'phone': '555-1234',
            'address': '123 Main St',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.customer.phone, '555-1234')

    def test_staff_user_without_customer_record_redirected(self):
        staff = make_staff_user(username='staffacc', role='admin')
        self.client.force_login(staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)


# ---------------------------------------------------------------------------
# Order history view
# ---------------------------------------------------------------------------

class OrderHistoryTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_customer_user(username='histuser', email='hist@example.com')
        self.url = reverse('customers:order_history')

    def test_unauthenticated_redirects(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f'/store/login/?next={self.url}')

    def test_shows_customer_orders(self):
        order = make_order(email=self.user.email)
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, order.order_number)

    def test_does_not_show_other_customer_orders(self):
        other_order = make_order(email='other@example.com')
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertNotContains(response, other_order.order_number)


# ---------------------------------------------------------------------------
# Order detail view (customer)
# ---------------------------------------------------------------------------

class CustomerOrderDetailTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_customer_user(username='detailuser', email='detail@example.com')
        self.order = make_order(email=self.user.email)
        self.url = reverse('customers:order_detail', args=[self.order.order_number])

    def test_customer_can_view_own_order(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.order_number)

    def test_status_steps_in_context(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertIn('status_steps', response.context)
        self.assertEqual(len(response.context['status_steps']), 5)

    def test_customer_cannot_view_other_order(self):
        other_order = make_order(email='other@example.com')
        self.client.force_login(self.user)
        url = reverse('customers:order_detail', args=[other_order.order_number])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
