from django import forms
from .models import Order


class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            }),
        }

    def __init__(self, *args, user_role=None, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance and user_role == 'staff':
            # Staff can only move forward, not cancel
            allowed = [(s, dict(Order.STATUS_CHOICES)[s])
                       for s in instance.next_statuses]
            self.fields['status'].choices = allowed
        elif instance and user_role in ('manager', 'admin'):
            # Manager/Admin can cancel too
            current_choices = list(Order.STATUS_CHOICES)
            self.fields['status'].choices = current_choices
