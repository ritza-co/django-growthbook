import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from .models import Order, OrderItem
from .forms import OrderStatusForm
from apps.core.decorators import role_required


@login_required
@role_required('admin', 'manager', 'staff')
def order_list(request):
    orders = Order.objects.select_related('created_by').all()

    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search = request.GET.get('search', '')

    if status_filter:
        orders = orders.filter(status=status_filter)

    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)

    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)

    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) | Q(customer_name__icontains=search)
        )

    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'orders/order_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
        'status_choices': Order.STATUS_CHOICES,
    })


@login_required
@role_required('admin', 'manager', 'staff')
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related('created_by').prefetch_related('items__product'), pk=pk)

    status_timeline = []
    statuses = ['pending', 'confirmed', 'processing', 'shipped', 'delivered']
    status_order = {s: i for i, s in enumerate(statuses)}
    current_idx = status_order.get(order.status, -1)

    for i, s in enumerate(statuses):
        if order.status == 'cancelled':
            status_timeline.append({'status': s, 'state': 'cancelled'})
        elif i < current_idx:
            status_timeline.append({'status': s, 'state': 'completed'})
        elif i == current_idx:
            status_timeline.append({'status': s, 'state': 'current'})
        else:
            status_timeline.append({'status': s, 'state': 'pending'})

    return render(request, 'orders/order_detail.html', {
        'order': order,
        'status_timeline': status_timeline,
    })


@login_required
@role_required('admin', 'manager', 'staff')
def order_update_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    user_role = request.user.profile.role

    if request.method == 'POST':
        new_status = request.POST.get('status')

        if user_role == 'staff':
            if new_status not in order.next_statuses:
                if request.headers.get('HX-Request'):
                    return HttpResponse('<p class="text-red-600">Invalid status transition.</p>', status=400)
                messages.error(request, 'Invalid status transition.')
                return redirect('orders:order_detail', pk=pk)

        if user_role in ('admin', 'manager'):
            allowed = [s for s, _ in Order.STATUS_CHOICES]
        else:
            allowed = order.next_statuses

        if new_status not in allowed:
            if request.headers.get('HX-Request'):
                return HttpResponse('<p class="text-red-600">Not allowed.</p>', status=403)
            raise PermissionDenied

        order.status = new_status
        order.save()
        messages.success(request, f'Order {order.order_number} status updated to {order.get_status_display()}.')

        if request.headers.get('HX-Request'):
            return render(request, 'orders/partials/status_badge.html', {'order': order})

        return redirect('orders:order_detail', pk=pk)

    form = OrderStatusForm(instance=order, user_role=user_role)
    if request.headers.get('HX-Request'):
        return render(request, 'orders/partials/status_form.html', {'form': form, 'order': order})

    return render(request, 'orders/order_update_status.html', {'form': form, 'order': order})


@login_required
@role_required('admin', 'manager', 'analyst')
def order_export_csv(request):
    orders = Order.objects.select_related('created_by').all()

    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search = request.GET.get('search', '')

    if status_filter:
        orders = orders.filter(status=status_filter)
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    if search:
        from django.db.models import Q
        orders = orders.filter(Q(order_number__icontains=search) | Q(customer_name__icontains=search))

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders.csv"'

    writer = csv.writer(response)
    writer.writerow(['Order Number', 'Customer Name', 'Customer Email', 'Customer Phone',
                     'Status', 'Total Amount', 'Created At', 'Created By'])

    for order in orders:
        writer.writerow([
            order.order_number,
            order.customer_name,
            order.customer_email,
            order.customer_phone,
            order.get_status_display(),
            order.total_amount,
            order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            order.created_by.username if order.created_by else '',
        ])

    return response
