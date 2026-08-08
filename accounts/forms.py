from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from core.validators import clean_ru_phone, clean_user_email

from .models import Profile

PASSWORD_HELP = 'Ваш пароль должен содержать как минимум 8 символов.'


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        label='Email',
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'autocomplete': 'email',
            'data-email-validate': '1',
            'placeholder': 'email@example.com',
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
    first_name = forms.CharField(
        label='Имя',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'autocomplete': 'given-name'}),
    )
    last_name = forms.CharField(
        label='Фамилия',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'autocomplete': 'family-name'}),
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Логин'
        self.fields['password1'].label = 'Пароль'
        self.fields['password2'].label = 'Подтверждение пароля'
        self.fields['password1'].help_text = PASSWORD_HELP
        self.fields['password2'].help_text = ''
        self.fields['username'].help_text = ''
        for name, field in self.fields.items():
            field.widget.attrs.setdefault('class', 'form-input')
            if name in ('password1', 'password2'):
                field.widget.attrs['data-password-toggle'] = '1'
                field.widget.attrs['autocomplete'] = 'new-password'

    def clean_phone(self):
        return clean_ru_phone(self.cleaned_data.get('phone', ''))

    def clean_email(self):
        return clean_user_email(self.cleaned_data.get('email', ''))

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.phone = self.cleaned_data['phone']
            profile.save(update_fields=['phone'])
        return user


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Логин'
        self.fields['password'].label = 'Пароль'
        for name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-input'
            if name == 'password':
                field.widget.attrs['data-password-toggle'] = '1'
                field.widget.attrs['autocomplete'] = 'current-password'


class ProfileForm(forms.ModelForm):
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

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone')
        labels = {
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'email': 'Email',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'autocomplete': 'family-name'}),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'autocomplete': 'email',
                'data-email-validate': '1',
                'placeholder': 'email@example.com',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile = getattr(self.instance, 'profile', None)
        if profile and not self.is_bound:
            self.fields['phone'].initial = profile.phone

    def clean_phone(self):
        return clean_ru_phone(self.cleaned_data.get('phone', ''))

    def clean_email(self):
        return clean_user_email(self.cleaned_data.get('email', ''))

    def save(self, commit=True):
        user = super().save(commit=commit)
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.phone = self.cleaned_data['phone']
        if commit:
            profile.save(update_fields=['phone'])
        return user
