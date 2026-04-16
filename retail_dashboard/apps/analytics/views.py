import csv
from datetime import datetime, timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, F
from django.utils import timezone
from apps.core.decorators import role_required
from apps.orders.models import Order, OrderItem
from apps.inventory.models import Product


@login_required
@role_required('admin', 'manager', 'analyst')
def analytics_dashboard(request):
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if not date_from:
        date_from = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = timezone.now().strftime('%Y-%m-%d')

    # Stock value summary
    stock_value = Product.objects.filter(is_active=True).aggregate(
        total=Sum(F('cost_price') * F('stock_quantity'))
    )['total'] or 0

    return render(request, 'analytics/dashboard.html', {
        'date_from': date_from,
        'date_to': date_to,
        'stock_value': stock_value,
    })


@login_required
@role_required('admin', 'manager', 'analyst')
def revenue_data(request):
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if not date_from:
        date_from = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = timezone.now().strftime('%Y-%m-%d')

    orders = Order.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
        status__in=['confirmed', 'processing', 'shipped', 'delivered']
    ).extra(select={'day': 'DATE(created_at)'}).values('day').annotate(
        revenue=Sum('total_amount')
    ).order_by('day')

    labels = [str(o['day']) for o in orders]
    data = [float(o['revenue']) for o in orders]

    return JsonResponse({'labels': labels, 'data': data})


@login_required
@role_required('admin', 'manager', 'analyst')
def top_products_data(request):
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if not date_from:
        date_from = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = timezone.now().strftime('%Y-%m-%d')

    top_products = OrderItem.objects.filter(
        order__created_at__date__gte=date_from,
        order__created_at__date__lte=date_to,
        order__status__in=['confirmed', 'processing', 'shipped', 'delivered']
    ).values('product__name').annotate(
        total_sold=Sum('quantity')
    ).order_by('-total_sold')[:10]

    labels = [p['product__name'] for p in top_products]
    data = [p['total_sold'] for p in top_products]

    return JsonResponse({'labels': labels, 'data': data})


@login_required
@role_required('admin', 'manager', 'analyst')
def order_status_data(request):
    status_counts = Order.objects.values('status').annotate(count=Count('id'))
    labels = []
    data = []
    colors = {
        'pending': '#FBBF24',
        'confirmed': '#3B82F6',
        'processing': '#6366F1',
        'shipped': '#8B5CF6',
        'delivered': '#10B981',
        'cancelled': '#EF4444',
    }
    bg_colors = []

    for item in status_counts:
        status = item['status']
        labels.append(dict(Order.STATUS_CHOICES).get(status, status))
        data.append(item['count'])
        bg_colors.append(colors.get(status, '#6B7280'))

    return JsonResponse({'labels': labels, 'data': data, 'colors': bg_colors})


@login_required
@role_required('admin', 'manager', 'analyst')
def analytics_export_csv(request):
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if not date_from:
        date_from = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = timezone.now().strftime('%Y-%m-%d')

    top_products = OrderItem.objects.filter(
        order__created_at__date__gte=date_from,
        order__created_at__date__lte=date_to,
        order__status__in=['confirmed', 'processing', 'shipped', 'delivered']
    ).values('product__name', 'product__sku').annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum(F('quantity') * F('unit_price'))
    ).order_by('-total_sold')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="analytics_{date_from}_{date_to}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Product Name', 'SKU', 'Total Units Sold', 'Total Revenue'])

    for item in top_products:
        writer.writerow([
            item['product__name'],
            item['product__sku'],
            item['total_sold'],
            item['total_revenue'],
        ])

    return response
