from django import forms

from core.validators import clean_ru_phone, clean_user_email


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
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Иван',
            'autocomplete': 'given-name',
        }),
    )
    phone = forms.CharField(
        label='Телефон',
        max_length=40,
        help_text='Для уточнения заказа и для связи с курьером',
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
            self.fields.pop('email')

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
        address = (cleaned.get('address') or '').strip()
        if method == self.DELIVERY_COURIER and not address:
            self.add_error('address', 'Укажите адрес доставки')
        if method == self.DELIVERY_PICKUP:
            cleaned['address'] = ''
        return cleaned
