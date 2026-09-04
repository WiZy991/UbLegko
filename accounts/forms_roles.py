from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import Group, User

from .roles import (
    ROLE_ADMIN,
    ROLE_CHOICES,
    ROLE_HELP,
    ROLE_USER,
    SEGMENT_CHOICES,
    apply_permissions_for_role,
    detect_group_role,
    detect_user_access_role,
    detect_user_segment,
    set_user_access_role,
    set_user_segment,
)


class SimpleGroupForm(forms.ModelForm):
    role = forms.ChoiceField(
        label='Права группы',
        choices=ROLE_CHOICES,
        help_text=(
            'Администратор — полный доступ. '
            'Персонал — заявки и запросы, кнопки «Готово», без удаления и настроек. '
            'Пользователь — обычный доступ на сайте (для VIP / постоянных / клиентов).'
        ),
    )
    use_role_template = forms.BooleanField(
        label='Заполнить права по шаблону роли',
        required=False,
        help_text=(
            'Включите, чтобы перезаписать список ниже шаблоном Администратор / Персонал / Пользователь. '
            'Выключите, чтобы сохранить свои детальные настройки.'
        ),
    )

    class Meta:
        model = Group
        fields = ('name', 'permissions')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['role'].initial = detect_group_role(self.instance)
            self.fields['use_role_template'].initial = False
        else:
            self.fields['role'].initial = ROLE_USER
            self.fields['use_role_template'].initial = True
        self.fields['permissions'].required = False
        self.fields['permissions'].label = 'Права'

    def save(self, commit=True):
        group = super().save(commit=False)
        self._pending_role = self.cleaned_data.get('role') or ROLE_USER
        self._pending_use_template = bool(self.cleaned_data.get('use_role_template'))
        if commit:
            group.save()
            self.apply_permissions(group)
        else:
            self.save_m2m = self._save_m2m
        return group

    def _save_m2m(self):
        self.apply_permissions(self.instance)

    def apply_permissions(self, group):
        role = getattr(self, '_pending_role', None) or self.cleaned_data.get('role') or ROLE_USER
        use_template = getattr(self, '_pending_use_template', None)
        if use_template is None:
            use_template = bool(self.cleaned_data.get('use_role_template'))
        if use_template:
            apply_permissions_for_role(group, role)
        else:
            perms = self.cleaned_data.get('permissions')
            if perms is not None:
                group.permissions.set(perms)


class UserRoleAdminForm(UserChangeForm):
    access_role = forms.ChoiceField(
        label='Права доступа',
        choices=ROLE_CHOICES,
        help_text=' · '.join(ROLE_HELP[k] for k, _ in ROLE_CHOICES),
    )
    customer_segment = forms.ChoiceField(
        label='Сегмент клиента',
        choices=SEGMENT_CHOICES,
        required=False,
        help_text=(
            'VIP — крупные покупки; постоянные — средняя активность; '
            'клиенты — остальные. Права сайта у всех сегментов одинаковые.'
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.instance
        if user and user.pk:
            self.fields['access_role'].initial = detect_user_access_role(user)
            self.fields['customer_segment'].initial = detect_user_segment(user)
        else:
            self.fields['access_role'].initial = ROLE_USER
            self.fields['customer_segment'].initial = ''
        for name in ('is_staff', 'is_superuser', 'user_permissions', 'groups'):
            self.fields.pop(name, None)

    def apply_access(self, user, *, actor=None):
        """Вызывается после save_model: админка сохраняет с commit=False."""
        role = self.cleaned_data.get('access_role') or ROLE_USER
        segment = self.cleaned_data.get('customer_segment') or ''
        set_user_access_role(user, role, actor=actor)
        set_user_segment(user, segment)


class UserRoleCreationForm(UserCreationForm):
    access_role = forms.ChoiceField(
        label='Права доступа',
        choices=ROLE_CHOICES,
        initial=ROLE_USER,
        help_text=ROLE_HELP[ROLE_ADMIN],
    )
    customer_segment = forms.ChoiceField(
        label='Сегмент клиента',
        choices=SEGMENT_CHOICES,
        required=False,
        initial='',
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name')

    def apply_access(self, user, *, actor=None):
        role = self.cleaned_data.get('access_role') or ROLE_USER
        segment = self.cleaned_data.get('customer_segment') or ''
        set_user_access_role(user, role, actor=actor)
        set_user_segment(user, segment)
