from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse

from .decorators import role_required


def _make_view():
    @role_required('admin', 'manager')
    def dummy_view(request):
        return HttpResponse('ok')
    return dummy_view


class RoleRequiredDecoratorTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = _make_view()

    def _user_with_role(self, role):
        user = User.objects.create_user(username=f'user_{role}', password='pass')
        user.profile.role = role
        user.profile.save()
        return user

    def test_unauthenticated_redirects_to_login(self):
        from django.contrib.auth.models import AnonymousUser
        request = self.factory.get('/fake/')
        request.user = AnonymousUser()
        response = self.view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_allowed_role_gets_200(self):
        request = self.factory.get('/fake/')
        request.user = self._user_with_role('admin')
        response = self.view(request)
        self.assertEqual(response.status_code, 200)

    def test_second_allowed_role_gets_200(self):
        request = self.factory.get('/fake/')
        request.user = self._user_with_role('manager')
        response = self.view(request)
        self.assertEqual(response.status_code, 200)

    def test_disallowed_role_raises_permission_denied(self):
        request = self.factory.get('/fake/')
        request.user = self._user_with_role('analyst')
        with self.assertRaises(PermissionDenied):
            self.view(request)

    def test_user_without_profile_raises_permission_denied(self):
        user = User.objects.create_user(username='no_profile', password='pass')
        user.profile.delete()
        user.refresh_from_db()
        request = self.factory.get('/fake/')
        request.user = user
        with self.assertRaises(PermissionDenied):
            self.view(request)
