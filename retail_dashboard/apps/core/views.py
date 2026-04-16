from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, F


@login_required
def dashboard(request):
    from apps.inventory.models import Product
    from apps.orders.models import Order

    user = request.user
    role = user.profile.role

    today = timezone.now().date()
    current_month_start = today.replace(day=1)

    context = {
        'role': role,
    }

    if role in ('admin', 'manager', 'analyst'):
        total_active_products = Product.objects.filter(is_active=True).count()
        low_stock_count = Product.objects.filter(
            is_active=True,
            stock_quantity__lte=F('reorder_threshold')
        ).count()
        context['total_active_products'] = total_active_products
        context['low_stock_count'] = low_stock_count

    if role in ('admin', 'manager', 'staff'):
        today_orders = Order.objects.filter(created_at__date=today).count()
        context['today_orders'] = today_orders

    if role in ('admin', 'manager', 'analyst'):
        month_revenue = Order.objects.filter(
            created_at__date__gte=current_month_start,
            status__in=['confirmed', 'processing', 'shipped', 'delivered']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        context['month_revenue'] = month_revenue

    recent_orders = Order.objects.select_related('created_by').order_by('-created_at')[:10]
    context['recent_orders'] = recent_orders

    if role in ('admin', 'manager'):
        low_stock_products = Product.objects.filter(
            is_active=True,
            stock_quantity__lte=F('reorder_threshold')
        ).select_related('category').order_by('stock_quantity')[:10]
        context['low_stock_products'] = low_stock_products

    return render(request, 'dashboard/index.html', context)


def custom_403(request, exception=None):
    return render(request, 'core/403.html', status=403)
