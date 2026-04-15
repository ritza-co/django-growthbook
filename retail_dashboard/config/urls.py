from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

handler403 = 'apps.core.views.custom_403'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.accounts.urls', namespace='accounts')),
    path('dashboard/', include('apps.core.urls', namespace='core')),
    path('inventory/', include('apps.inventory.urls', namespace='inventory')),
    path('orders/', include('apps.orders.urls', namespace='orders')),
    path('analytics/', include('apps.analytics.urls', namespace='analytics')),
    path('users/', include('apps.users.urls', namespace='users')),
    path('profile/', include('apps.accounts.profile_urls', namespace='profile')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
