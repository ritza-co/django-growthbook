from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('', views.analytics_dashboard, name='dashboard'),
    path('data/revenue/', views.revenue_data, name='revenue_data'),
    path('data/top-products/', views.top_products_data, name='top_products_data'),
    path('data/order-status/', views.order_status_data, name='order_status_data'),
    path('export/', views.analytics_export_csv, name='export_csv'),
]
