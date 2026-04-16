from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from apps.orders.models import Order
from .forms import CustomerRegisterForm, CustomerLoginForm, CustomerAccountForm
from .models import Customer


def register(request):
    if request.method == 'POST':
        form = CustomerRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()
            # Remove the auto-created Profile (created by accounts signal) so
            # this user is recognized as a customer, not internal staff.
            user.profile.delete()
            Customer.objects.create(user=user)
            login(request, user)
            return redirect('storefront:home')
    else:
        form = CustomerRegisterForm()
    return render(request, 'customers/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'customer'):
            return redirect('storefront:home')
        return redirect('storefront:home')

    if request.method == 'POST':
        form = CustomerLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                # Block internal staff from logging in through customer portal
                if hasattr(user, 'profile') and not hasattr(user, 'customer'):
                    form.add_error(None, 'This account is not a customer account. Please use the internal login.')
                else:
                    login(request, user)
                    next_url = request.GET.get('next', 'storefront:home')
                    return redirect(next_url)
            else:
                form.add_error(None, 'Invalid username or password.')
    else:
        form = CustomerLoginForm()
    return render(request, 'customers/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('customers:login')


@login_required(login_url='/store/login/')
def account(request):
    if not hasattr(request.user, 'customer'):
        return redirect('storefront:home')

    customer = request.user.customer
    if request.method == 'POST':
        form = CustomerAccountForm(request.POST)
        if form.is_valid():
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.save()
            customer.phone = form.cleaned_data['phone']
            customer.address = form.cleaned_data['address']
            customer.save()
            messages.success(request, 'Account updated successfully.')
            return redirect('customers:account')
    else:
        form = CustomerAccountForm(initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'phone': customer.phone,
            'address': customer.address,
        })
    return render(request, 'customers/account.html', {'form': form, 'customer': customer})


@login_required(login_url='/store/login/')
def order_history(request):
    if not hasattr(request.user, 'customer'):
        return redirect('storefront:home')

    orders = Order.objects.filter(customer_email=request.user.email).order_by('-created_at')
    return render(request, 'storefront/order_history.html', {'orders': orders})


@login_required(login_url='/store/login/')
def order_detail(request, order_number):
    if not hasattr(request.user, 'customer'):
        return redirect('storefront:home')

    order = get_object_or_404(Order, order_number=order_number, customer_email=request.user.email)
    status_steps = ['pending', 'confirmed', 'processing', 'shipped', 'delivered']
    return render(request, 'storefront/order_detail.html', {'order': order, 'status_steps': status_steps})
