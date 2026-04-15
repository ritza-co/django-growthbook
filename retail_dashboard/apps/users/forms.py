from django import forms
from django.contrib.auth.models import User
from apps.accounts.models import Profile

INPUT_CLASS = 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'


class UserCreateForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': INPUT_CLASS}))
    first_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': INPUT_CLASS}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': INPUT_CLASS}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': INPUT_CLASS}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': INPUT_CLASS}))
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES, widget=forms.Select(attrs={'class': INPUT_CLASS}))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': INPUT_CLASS}))

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('A user with that username already exists.')
        return username


class UserEditForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': INPUT_CLASS}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': INPUT_CLASS}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': INPUT_CLASS}))
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES, widget=forms.Select(attrs={'class': INPUT_CLASS}))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': INPUT_CLASS}))
    is_active = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={
        'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
    }))
