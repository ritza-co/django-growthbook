from functools import wraps
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """
    Decorator that checks if the logged-in user has one of the allowed roles.
    Roles: admin, manager, analyst, staff
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            try:
                user_role = request.user.profile.role
            except AttributeError:
                raise PermissionDenied
            if user_role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
