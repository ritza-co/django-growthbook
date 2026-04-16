from django.test import TestCase
from django.contrib.auth.models import User
from .models import Profile


class ProfileSignalTest(TestCase):
    """Profile is auto-created via signal when a User is saved."""

    def test_profile_created_on_user_creation(self):
        user = User.objects.create_user(username='testuser', password='pass')
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, Profile)

    def test_profile_default_role_is_staff(self):
        user = User.objects.create_user(username='testuser', password='pass')
        self.assertEqual(user.profile.role, 'staff')

    def test_profile_not_created_on_update(self):
        user = User.objects.create_user(username='testuser', password='pass')
        profile_id = user.profile.pk
        user.first_name = 'Updated'
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.profile.pk, profile_id)


class ProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin_user', password='pass')
        self.user.profile.role = 'admin'
        self.user.profile.save()

    def test_str_representation(self):
        self.assertIn('admin_user', str(self.user.profile))
        self.assertIn('Admin', str(self.user.profile))

    def test_role_color_admin(self):
        self.assertEqual(self.user.profile.role_color, 'red')

    def test_role_color_manager(self):
        self.user.profile.role = 'manager'
        self.assertEqual(self.user.profile.role_color, 'blue')

    def test_role_color_analyst(self):
        self.user.profile.role = 'analyst'
        self.assertEqual(self.user.profile.role_color, 'green')

    def test_role_color_staff(self):
        self.user.profile.role = 'staff'
        self.assertEqual(self.user.profile.role_color, 'yellow')

    def test_role_color_unknown(self):
        self.user.profile.role = 'unknown'
        self.assertEqual(self.user.profile.role_color, 'gray')
