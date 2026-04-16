from django.urls import path
from . import views

app_name = 'storefront'

urlpatterns = [
    path('', views.homepage, name='home'),
    path('products/', views.product_catalog, name='catalog'),
    path('products/<slug:slug>/', views.product_detail, name='product_detail'),
    path('category/<slug:slug>/', views.category_view, name='category'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/update/', views.cart_update, name='cart_update'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/confirm/<str:order_number>/', views.order_confirm, name='order_confirm'),
    path('orders/track/', views.track_order, name='track_order'),
    path('review/<int:product_id>/', views.submit_review, name='submit_review'),
]
