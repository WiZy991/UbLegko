from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import Group, User

from .roles import (
    ROLE_ADMIN,
    ROLE_CHOICES,
    ROLE_HELP,
    ROLE_STAFF,
    ROLE_USER,
    MEMBERSHIP_CHOICES,
    SEGMENT_BASE,
    apply_permissions_for_role,
    detect_group_role,
    detect_user_access_role,
    detect_user_membership,
    set_user_membership,
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
    customer_group = forms.ChoiceField(
        label='Группа',
        choices=MEMBERSHIP_CHOICES,
        required=False,
        help_text=(
            'Выбор группы сразу выставляет права: '
            'Администраторы / Персонал / VIP / постоянные / клиенты.'
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.instance
        if user and user.pk:
            self.fields['access_role'].initial = detect_user_access_role(user)
            self.fields['customer_group'].initial = detect_user_membership(user)
        else:
            self.fields['access_role'].initial = ROLE_USER
            self.fields['customer_group'].initial = SEGMENT_BASE
        for name in ('is_staff', 'is_superuser', 'user_permissions', 'groups'):
            self.fields.pop(name, None)

    def apply_access(self, user, *, actor=None):
        """Группа — источник истины: по ней выставляются и права."""
        membership = self.cleaned_data.get('customer_group')
        if membership is None:
            membership = ''
        set_user_membership(user, membership, actor=actor)


class UserRoleCreationForm(UserCreationForm):
    access_role = forms.ChoiceField(
        label='Права доступа',
        choices=ROLE_CHOICES,
        initial=ROLE_USER,
        help_text=ROLE_HELP[ROLE_ADMIN],
    )
    customer_group = forms.ChoiceField(
        label='Группа',
        choices=MEMBERSHIP_CHOICES,
        required=False,
        initial=SEGMENT_BASE,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name')

    def apply_access(self, user, *, actor=None):
        membership = self.cleaned_data.get('customer_group')
        if membership:
            set_user_membership(user, membership, actor=actor)
            return
        role = self.cleaned_data.get('access_role') or ROLE_USER
        if role == ROLE_ADMIN:
            set_user_membership(user, ROLE_ADMIN, actor=actor)
        elif role == ROLE_STAFF:
            set_user_membership(user, ROLE_STAFF, actor=actor)
        else:
            set_user_membership(user, '', actor=actor)
