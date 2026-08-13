from django import forms

from accounts.models import DeliveryAddress
from core.validators import clean_ru_phone

NAME_HELP = 'Как к вам обращаться'
PHONE_HELP = 'Для уточнения заказа и для связи с курьером'

_STREET_PREFIXES = (
    'ул.', 'ул ', 'улица ',
    'пр.', 'пр ', 'пр-т', 'просп.', 'проспект ',
    'пер.', 'пер ', 'переулок ',
    'б-р', 'бул.', 'ш.', 'шоссе ', 'наб.', 'набережная ',
    'мкр.', 'мкр ', 'микрорайон ',
)


def extract_city_from_address(address: str) -> str:
    """Первый сегмент адреса до запятой, если это не улица."""
    address = (address or '').strip()
    if not address:
        return ''
    first = address.split(',')[0].strip()
    if not first:
        return ''
    lower = first.lower()
    if any(lower.startswith(prefix) for prefix in _STREET_PREFIXES):
        return ''
    if lower.startswith('г.'):
        first = first[2:].strip()
    elif lower.startswith('г '):
        first = first[2:].strip()
    elif lower.startswith('город '):
        first = first[6:].strip()
    return first


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
    site_feedback = forms.CharField(
        label='Замечания по сайту',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 3,
            'placeholder': 'Замечания/Недостатки/Что неудобно/Что нам улучшить?',
        }),
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        if not user or not user.is_authenticated:
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
            # Самовывоз — адрес не нужен, не валим форму из‑за hidden select
            method = ''
            if self.is_bound:
                method = (self.data.get('delivery_method') or '').strip()
            if method == self.DELIVERY_PICKUP:
                self.fields['saved_address'].required = False
        else:
            self.fields.pop('saved_address')

    @staticmethod
    def city_label(city):
        if city.note:
            return f'{city.display_name} — {city.note}'
        return city.display_name

    @staticmethod
    def order_city_label(*, delivery_method, address, selected_city):
        if delivery_method != CheckoutForm.DELIVERY_COURIER:
            return CheckoutForm.city_label(selected_city) if selected_city else ''
        from_address = extract_city_from_address(address)
        if from_address:
            return from_address
        return CheckoutForm.city_label(selected_city) if selected_city else ''

    def clean_phone(self):
        return clean_ru_phone(self.cleaned_data.get('phone', ''))

    def clean(self):
        cleaned = super().clean()
        method = cleaned.get('delivery_method')
        if method == self.DELIVERY_PICKUP:
            cleaned['address'] = ''
            cleaned['address_name'] = ''
            return cleaned

        saved = cleaned.get('saved_address')
        if saved is not None:
            cleaned['address'] = saved.address
            cleaned['address_name'] = saved.name
        else:
            address = (cleaned.get('address') or '').strip()
            cleaned['address'] = address
            cleaned['address_name'] = ''
            if not address:
                self.add_error(
                    'address' if 'address' in self.fields else 'saved_address',
                    'Укажите адрес доставки',
                )
        return cleaned
