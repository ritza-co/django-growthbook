from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('export/', views.order_export_csv, name='order_export_csv'),
    path('<int:pk>/', views.order_detail, name='order_detail'),
    path('<int:pk>/update-status/', views.order_update_status, name='order_update_status'),
]
