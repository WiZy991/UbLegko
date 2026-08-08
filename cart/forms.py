from django import forms

from core.validators import clean_ru_phone, clean_user_email


class CheckoutForm(forms.Form):
    full_name = forms.CharField(
        label='ФИО',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Иванов Иван Иванович',
            'autocomplete': 'name',
        }),
    )
    phone = forms.CharField(
        label='Телефон',
        max_length=40,
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

    def clean_phone(self):
        return clean_ru_phone(self.cleaned_data.get('phone', ''))

    def clean_email(self):
        return clean_user_email(self.cleaned_data.get('email', ''))
