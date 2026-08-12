from django import forms

from .validators import clean_ru_phone


class StainHelpForm(forms.Form):
    """Обращение «Что-то не отмывается»."""

    problem = forms.CharField(
        label='Что не отмывается',
        max_length=2000,
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 4,
            'placeholder': 'Опишите пятно или поверхность, что уже пробовали…',
        }),
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
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '+7 (999) 000-00-00',
            'inputmode': 'tel',
            'autocomplete': 'tel',
            'data-phone-mask': '1',
        }),
    )
    contact_method = forms.CharField(
        label='Способ связи',
        max_length=300,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Звонок, WhatsApp, Telegram, MAX…',
        }),
    )

    def clean_phone(self):
        return clean_ru_phone(self.cleaned_data['phone'])

    def clean_full_name(self):
        name = (self.cleaned_data.get('full_name') or '').strip()
        if len(name) < 2:
            raise forms.ValidationError('Укажите имя')
        return name

    def clean_problem(self):
        text = (self.cleaned_data.get('problem') or '').strip()
        if len(text) < 3:
            raise forms.ValidationError('Опишите, что не отмывается')
        return text

    def clean_contact_method(self):
        text = (self.cleaned_data.get('contact_method') or '').strip()
        if len(text) < 2:
            raise forms.ValidationError('Укажите удобный способ связи')
        return text
