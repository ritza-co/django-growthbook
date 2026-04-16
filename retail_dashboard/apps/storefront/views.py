from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.inventory.models import Category, Product
from apps.orders.models import Order, OrderItem
from apps.storefront.models import Review


def homepage(request):
    featured_products = Product.objects.filter(is_featured=True, is_active=True).select_related('category')[:8]
    categories = Category.objects.all()
    return render(request, 'storefront/home.html', {
        'featured_products': featured_products,
        'categories': categories,
    })


def product_catalog(request):
    products = Product.objects.filter(is_active=True).select_related('category')

    category_slug = request.GET.get('category')
    if category_slug:
        products = products.filter(category__slug=category_slug)

    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    if price_min:
        try:
            products = products.filter(price__gte=Decimal(price_min))
        except Exception:
            pass
    if price_max:
        try:
            products = products.filter(price__lte=Decimal(price_max))
        except Exception:
            pass

    in_stock = request.GET.get('in_stock')
    if in_stock:
        products = products.filter(stock_quantity__gt=0)

    sort = request.GET.get('sort', '-created_at')
    allowed_sorts = ['price', '-price', 'name', '-name', '-created_at', 'created_at']
    if sort in allowed_sorts:
        products = products.order_by(sort)

    paginator = Paginator(products, 24)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()
    selected_category = None
    if category_slug:
        selected_category = Category.objects.filter(slug=category_slug).first()

    return render(request, 'storefront/catalog.html', {
        'page_obj': page_obj,
        'categories': categories,
        'selected_category': selected_category,
        'category_slug': category_slug or '',
        'price_min': price_min or '',
        'price_max': price_max or '',
        'in_stock': in_stock or '',
        'sort': sort,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    reviews = product.reviews.select_related('customer__user').all()
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True,
    ).exclude(pk=product.pk)[:4]

    user_review = None
    if request.user.is_authenticated and hasattr(request.user, 'customer'):
        user_review = reviews.filter(customer=request.user.customer).first()

    return render(request, 'storefront/product_detail.html', {
        'product': product,
        'reviews': reviews,
        'related_products': related_products,
        'user_review': user_review,
    })


def category_view(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category=category, is_active=True).select_related('category')

    sort = request.GET.get('sort', '-created_at')
    allowed_sorts = ['price', '-price', 'name', '-name', '-created_at', 'created_at']
    if sort in allowed_sorts:
        products = products.order_by(sort)

    paginator = Paginator(products, 24)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'storefront/catalog.html', {
        'page_obj': page_obj,
        'categories': Category.objects.all(),
        'selected_category': category,
        'category_slug': slug,
        'price_min': '',
        'price_max': '',
        'in_stock': '',
        'sort': sort,
    })


def cart_view(request):
    cart = request.session.get('cart', {})
    cart_items = []
    subtotal = Decimal('0.00')

    for product_id, item in cart.items():
        try:
            product = Product.objects.get(pk=int(product_id), is_active=True)
            quantity = item['quantity']
            unit_price = Decimal(str(item['unit_price']))
            line_total = unit_price * quantity
            subtotal += line_total
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'unit_price': unit_price,
                'line_total': line_total,
            })
        except (Product.DoesNotExist, Exception):
            continue

    return render(request, 'storefront/cart.html', {
        'cart_items': cart_items,
        'subtotal': subtotal,
    })


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    cart = request.session.get('cart', {})
    key = str(product_id)
    quantity = int(request.POST.get('quantity', 1))

    if key in cart:
        cart[key]['quantity'] += quantity
    else:
        cart[key] = {
            'quantity': quantity,
            'unit_price': str(product.price),
        }

    request.session['cart'] = cart
    request.session.modified = True

    cart_count = sum(item['quantity'] for item in cart.values())

    if request.headers.get('HX-Request'):
        return render(request, 'storefront/_cart_count.html', {'cart_count': cart_count})

    return redirect('storefront:cart')


@require_POST
def cart_update(request):
    cart = request.session.get('cart', {})
    product_id = str(request.POST.get('product_id', ''))
    quantity = int(request.POST.get('quantity', 1))

    if product_id in cart:
        if quantity <= 0:
            del cart[product_id]
        else:
            cart[product_id]['quantity'] = quantity

    request.session['cart'] = cart
    request.session.modified = True

    if request.headers.get('HX-Request'):
        cart_items = []
        subtotal = Decimal('0.00')
        for pid, item in cart.items():
            try:
                product = Product.objects.get(pk=int(pid), is_active=True)
                qty = item['quantity']
                unit_price = Decimal(str(item['unit_price']))
                line_total = unit_price * qty
                subtotal += line_total
                cart_items.append({
                    'product': product,
                    'quantity': qty,
                    'unit_price': unit_price,
                    'line_total': line_total,
                })
            except (Product.DoesNotExist, Exception):
                continue
        return render(request, 'storefront/_cart_items.html', {
            'cart_items': cart_items,
            'subtotal': subtotal,
        })

    return redirect('storefront:cart')


@require_POST
def cart_remove(request, product_id):
    cart = request.session.get('cart', {})
    key = str(product_id)
    if key in cart:
        del cart[key]
    request.session['cart'] = cart
    request.session.modified = True

    if request.headers.get('HX-Request'):
        cart_items = []
        subtotal = Decimal('0.00')
        for pid, item in cart.items():
            try:
                product = Product.objects.get(pk=int(pid), is_active=True)
                qty = item['quantity']
                unit_price = Decimal(str(item['unit_price']))
                line_total = unit_price * qty
                subtotal += line_total
                cart_items.append({
                    'product': product,
                    'quantity': qty,
                    'unit_price': unit_price,
                    'line_total': line_total,
                })
            except (Product.DoesNotExist, Exception):
                continue
        return render(request, 'storefront/_cart_items.html', {
            'cart_items': cart_items,
            'subtotal': subtotal,
        })

    return redirect('storefront:cart')


@login_required(login_url='/store/login/')
def checkout(request):
    if not hasattr(request.user, 'customer'):
        messages.error(request, 'You need a customer account to checkout.')
        return redirect('storefront:cart')

    customer = request.user.customer
    cart = request.session.get('cart', {})

    if not cart:
        messages.error(request, 'Your cart is empty.')
        return redirect('storefront:cart')

    # Build cart items with product data
    cart_items = []
    for product_id, item in cart.items():
        try:
            product = Product.objects.get(pk=int(product_id), is_active=True)
            cart_items.append({
                'product': product,
                'product_id': int(product_id),
                'quantity': item['quantity'],
                'unit_price': Decimal(str(item['unit_price'])),
                'line_total': Decimal(str(item['unit_price'])) * item['quantity'],
            })
        except Product.DoesNotExist:
            continue

    subtotal = sum(item['line_total'] for item in cart_items)

    if request.method == 'POST':
        # Validate stock for all items
        errors = []
        for item in cart_items:
            if item['product'].stock_quantity < item['quantity']:
                errors.append(
                    f"Not enough stock for {item['product'].name}. "
                    f"Available: {item['product'].stock_quantity}, requested: {item['quantity']}."
                )

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'storefront/checkout.html', {
                'cart_items': cart_items,
                'subtotal': subtotal,
                'customer': customer,
            })

        # Get or create the storefront system user
        storefront_user, _ = User.objects.get_or_create(
            username='storefront',
            defaults={
                'is_active': True,
                'first_name': 'Storefront',
                'last_name': 'System',
            },
        )

        # Create order
        order = Order.objects.create(
            customer_name=request.user.get_full_name() or request.user.username,
            customer_email=request.user.email,
            customer_phone=customer.phone,
            source='storefront',
            created_by=storefront_user,
        )

        # Create order items and decrement stock
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                quantity=item['quantity'],
                unit_price=item['unit_price'],
            )
            Product.objects.filter(pk=item['product_id']).update(
                stock_quantity=F('stock_quantity') - item['quantity']
            )

        order.compute_total()

        # Clear cart
        request.session['cart'] = {}
        request.session.modified = True

        return redirect('storefront:order_confirm', order_number=order.order_number)

    return render(request, 'storefront/checkout.html', {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'customer': customer,
    })


STATUS_STEPS = ['pending', 'confirmed', 'processing', 'shipped', 'delivered']


def order_confirm(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, 'storefront/order_confirm.html', {
        'order': order,
        'status_steps': STATUS_STEPS,
    })


def track_order(request):
    order = None
    error = None
    if request.method == 'POST':
        order_number = request.POST.get('order_number', '').strip()
        if order_number:
            try:
                order = Order.objects.prefetch_related('items__product').get(order_number=order_number)
            except Order.DoesNotExist:
                error = f'No order found with number "{order_number}".'
        else:
            error = 'Please enter an order number.'
    return render(request, 'storefront/track_order.html', {
        'order': order,
        'error': error,
        'status_steps': STATUS_STEPS,
    })


@require_POST
@login_required(login_url='/store/login/')
def submit_review(request, product_id):
    if not hasattr(request.user, 'customer'):
        if request.headers.get('HX-Request'):
            return HttpResponse('<p class="text-red-600">You must be a customer to submit a review.</p>')
        return redirect('storefront:home')

    product = get_object_or_404(Product, pk=product_id, is_active=True)
    customer = request.user.customer

    rating = request.POST.get('rating')
    comment = request.POST.get('comment', '').strip()

    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError
    except (TypeError, ValueError):
        if request.headers.get('HX-Request'):
            return HttpResponse('<p class="text-red-600">Please provide a rating between 1 and 5.</p>')
        messages.error(request, 'Please provide a rating between 1 and 5.')
        return redirect('storefront:product_detail', slug=product.slug)

    review, created = Review.objects.update_or_create(
        product=product,
        customer=customer,
        defaults={'rating': rating, 'comment': comment},
    )

    if request.headers.get('HX-Request'):
        return render(request, 'storefront/_review_success.html', {
            'review': review,
            'created': created,
        })

    messages.success(request, 'Your review has been submitted.')
    return redirect('storefront:product_detail', slug=product.slug)
