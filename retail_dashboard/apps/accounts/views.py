from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import CustomLoginForm, ProfileForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_active:
                messages.error(request, 'Your account has been deactivated. Please contact an administrator.')
                return render(request, 'accounts/login.html', {'form': form})
            login(request, user)
            next_url = request.GET.get('next', '/dashboard/')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = CustomLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def profile_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        user_first_name = request.POST.get('first_name', '')
        user_last_name = request.POST.get('last_name', '')
        user_email = request.POST.get('email', '')

        if form.is_valid():
            form.save()
            user = request.user
            user.first_name = user_first_name
            user.last_name = user_last_name
            user.email = user_email
            user.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile:view')
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'profile/detail.html', {'form': form, 'profile': profile})
