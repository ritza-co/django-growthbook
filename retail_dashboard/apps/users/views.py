from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from apps.core.decorators import role_required
from apps.accounts.models import Profile
from .forms import UserCreateForm, UserEditForm


@login_required
@role_required('admin')
def user_list(request):
    users = User.objects.select_related('profile').order_by('username')
    return render(request, 'users/user_list.html', {'users': users})


@login_required
@role_required('admin')
def user_create(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
            )
            # Profile is auto-created by signal; update it
            profile = user.profile
            profile.role = form.cleaned_data['role']
            profile.phone = form.cleaned_data['phone']
            profile.save()
            messages.success(request, f'User "{user.username}" created successfully.')
            return redirect('users:user_list')
    else:
        form = UserCreateForm()

    return render(request, 'users/user_form.html', {'form': form, 'action': 'Create'})


@login_required
@role_required('admin')
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile = user.profile

    if request.method == 'POST':
        form = UserEditForm(request.POST)
        if form.is_valid():
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.is_active = form.cleaned_data['is_active']
            user.save()

            profile.role = form.cleaned_data['role']
            profile.phone = form.cleaned_data['phone']
            profile.save()

            messages.success(request, f'User "{user.username}" updated successfully.')
            return redirect('users:user_list')
    else:
        form = UserEditForm(initial={
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'role': profile.role,
            'phone': profile.phone,
            'is_active': user.is_active,
        })

    return render(request, 'users/user_form.html', {'form': form, 'edit_user': user, 'action': 'Edit'})


@login_required
@role_required('admin')
def user_deactivate(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        if user == request.user:
            messages.error(request, 'You cannot deactivate your own account.')
            return redirect('users:user_list')
        user.is_active = False
        user.save()
        messages.success(request, f'User "{user.username}" has been deactivated.')
        return redirect('users:user_list')
    return render(request, 'users/user_confirm_deactivate.html', {'edit_user': user})
