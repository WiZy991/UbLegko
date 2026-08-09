from django import forms

from accounts.models import DeliveryAddress
from core.validators import clean_ru_phone, clean_user_email

NAME_HELP = 'Как к вам обращаться'
PHONE_HELP = 'Для уточнения заказа и для связи с курьером'


class CheckoutForm(forms.Form):
    DELIVERY_COURIER = 'courier'
    DELIVERY_PICKUP = 'pickup'
    DELIVERY_CHOICES = (
        (DELIVERY_COURIER, 'Курьером'),
        (DELIVERY_PICKUP, 'Самовывоз'),
    )

    delivery_method = forms.ChoiceField(
        label='Способ получения',
        choices=DELIVERY_CHOICES,
        initial=DELIVERY_COURIER,
        widget=forms.RadioSelect,
    )
    full_name = forms.CharField(
        label='Имя',
        max_length=200,
        help_text=NAME_HELP,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Иван',
            'autocomplete': 'given-name',
        }),
    )
    phone = forms.CharField(
        label='Телефон',
        max_length=40,
        help_text=PHONE_HELP,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '+7 (999) 000-00-00',
            'inputmode': 'tel',
            'autocomplete': 'tel',
            'data-phone-mask': '1',
        }),
    )
    email = forms.EmailField(
        label='Email',
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'email@example.com',
            'autocomplete': 'email',
            'data-email-validate': '1',
        }),
    )
    saved_address = forms.ModelChoiceField(
        label='Адрес доставки',
        queryset=DeliveryAddress.objects.none(),
        required=False,
        empty_label=None,
        widget=forms.Select(attrs={'class': 'form-input'}),
    )
    address = forms.CharField(
        label='Адрес доставки',
        max_length=400,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Город, улица, дом, квартира',
            'autocomplete': 'street-address',
        }),
    )
    comment = forms.CharField(
        label='Комментарий',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 4,
            'placeholder': 'Комментарий к заявке',
        }),
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if not user or not user.is_authenticated:
            self.fields.pop('email', None)
            self.fields.pop('saved_address', None)
            return

        addresses = DeliveryAddress.objects.filter(user=user)
        if addresses.exists():
            self.fields['saved_address'].queryset = addresses
            self.fields['saved_address'].required = True
            self.fields['saved_address'].label_from_instance = (
                lambda obj: f'{obj.name} — {obj.address}'
            )
            self.fields.pop('address')
            if not self.is_bound:
                default = addresses.filter(is_default=True).first() or addresses.first()
                self.fields['saved_address'].initial = default
        else:
            self.fields.pop('saved_address')

    def clean_phone(self):
        return clean_ru_phone(self.cleaned_data.get('phone', ''))

    def clean_email(self):
        value = self.cleaned_data.get('email', '')
        if not value:
            return ''
        return clean_user_email(value)

    def clean(self):
        cleaned = super().clean()
        method = cleaned.get('delivery_method')
        if method == self.DELIVERY_PICKUP:
            cleaned['address'] = ''
            return cleaned

        saved = cleaned.get('saved_address')
        if saved is not None:
            cleaned['address'] = saved.address
        else:
            address = (cleaned.get('address') or '').strip()
            cleaned['address'] = address
            if not address:
                self.add_error(
                    'address' if 'address' in self.fields else 'saved_address',
                    'Укажите адрес доставки',
                )
        return cleaned
