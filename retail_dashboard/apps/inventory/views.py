import csv
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Product, Category, StockMovement
from .forms import ProductForm, CSVImportForm
from apps.core.decorators import role_required


@login_required
@role_required('admin', 'manager')
def product_list(request):
    products = Product.objects.select_related('category').filter(is_active=True)

    search = request.GET.get('search', '')
    category_id = request.GET.get('category', '')
    stock_status = request.GET.get('stock_status', '')

    if search:
        products = products.filter(Q(name__icontains=search) | Q(sku__icontains=search))

    if category_id:
        products = products.filter(category_id=category_id)

    if stock_status == 'in_stock':
        from django.db.models import F
        products = products.filter(stock_quantity__gt=F('reorder_threshold'))
    elif stock_status == 'low_stock':
        from django.db.models import F
        products = products.filter(stock_quantity__lte=F('reorder_threshold'), stock_quantity__gt=0)
    elif stock_status == 'out_of_stock':
        products = products.filter(stock_quantity=0)

    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()

    return render(request, 'inventory/product_list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'search': search,
        'selected_category': category_id,
        'stock_status': stock_status,
    })


@login_required
@role_required('admin', 'manager')
def product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Product "{product.name}" created successfully.')
            return redirect('inventory:product_detail', pk=product.pk)
    else:
        form = ProductForm()

    return render(request, 'inventory/product_form.html', {'form': form, 'action': 'Add'})


@login_required
@role_required('admin', 'manager')
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    movements = product.stock_movements.select_related('created_by').order_by('-created_at')[:20]

    return render(request, 'inventory/product_detail.html', {
        'product': product,
        'movements': movements,
    })


@login_required
@role_required('admin', 'manager')
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Product "{product.name}" updated successfully.')
            return redirect('inventory:product_detail', pk=product.pk)
    else:
        form = ProductForm(instance=product)

    return render(request, 'inventory/product_form.html', {'form': form, 'product': product, 'action': 'Edit'})


@login_required
@role_required('admin', 'manager')
def product_deactivate(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.is_active = False
        product.save()
        messages.success(request, f'Product "{product.name}" deactivated.')
        return redirect('inventory:product_list')
    return render(request, 'inventory/product_confirm_deactivate.html', {'product': product})


@login_required
@role_required('admin')
def product_import(request):
    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            decoded_file = csv_file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(decoded_file))
            created_count = 0
            errors = []

            for row_num, row in enumerate(reader, start=2):
                try:
                    category_name = row.get('category', '').strip()
                    category = None
                    if category_name:
                        category, _ = Category.objects.get_or_create(
                            name=category_name,
                            defaults={'slug': category_name.lower().replace(' ', '-')}
                        )

                    sku = row.get('sku', '').strip()
                    if not sku:
                        errors.append(f"Row {row_num}: SKU is required.")
                        continue

                    product, created = Product.objects.update_or_create(
                        sku=sku,
                        defaults={
                            'name': row.get('name', '').strip(),
                            'description': row.get('description', '').strip(),
                            'category': category,
                            'price': float(row.get('price', 0)),
                            'cost_price': float(row.get('cost_price', 0)),
                            'stock_quantity': int(row.get('stock_quantity', 0)),
                            'reorder_threshold': int(row.get('reorder_threshold', 10)),
                            'is_active': row.get('is_active', 'true').lower() == 'true',
                        }
                    )
                    if created:
                        created_count += 1
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")

            if errors:
                for error in errors:
                    messages.warning(request, error)

            messages.success(request, f'Imported {created_count} new products successfully.')
            return redirect('inventory:product_list')
    else:
        form = CSVImportForm()

    return render(request, 'inventory/product_import.html', {'form': form})
