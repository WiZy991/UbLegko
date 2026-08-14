from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from cart.models import Order

from .forms import (
    DeliveryAddressForm,
    LoginForm,
    PasswordResetConfirmForm,
    PasswordResetRequestForm,
    ProfileForm,
    RegisterForm,
    ResendEmailConfirmForm,
)
from .models import DeliveryAddress, Profile
from .tokens import email_confirm_token
from .utils import send_email_confirmation


class UserLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    next_page = 'catalog:home'


class UserPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/email/password_reset_email.txt'
    subject_template_name = 'accounts/email/password_reset_subject.txt'
    form_class = PasswordResetRequestForm
    success_url = reverse_lazy('accounts:password_reset_done')

    def form_valid(self, form):
        from core.models import SiteSettings

        self.extra_email_context = {
            'site_name': SiteSettings.load().brand_name,
        }
        return super().form_valid(form)


class UserPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    form_class = PasswordResetConfirmForm
    success_url = reverse_lazy('accounts:profile')
    post_reset_login = True
    post_reset_login_backend = 'django.contrib.auth.backends.ModelBackend'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Пароль изменён. Вы вошли в личный кабинет.')
        return response


def register(request):
    if request.user.is_authenticated:
        return redirect('accounts:profile')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            request.session['pending_verify_email'] = user.email
            try:
                send_email_confirmation(request, user)
            except Exception:
                messages.warning(
                    request,
                    'Аккаунт создан, но письмо не удалось отправить. '
                    'Запросите повторную отправку ниже.',
                )
                return redirect('accounts:resend_email_confirm')
            messages.success(
                request,
                'Аккаунт создан. Подтвердите email — письмо уже отправлено.',
            )
            return redirect('accounts:register_done')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def register_done(request):
    email = request.session.get('pending_verify_email', '')
    return render(request, 'accounts/register_done.html', {'email': email})


def confirm_email(request, uidb64, token):
    user = _get_user_from_uid(uidb64)
    if user is None or not email_confirm_token.check_token(user, token):
        messages.error(
            request,
            'Ссылка подтверждения недействительна или устарела. Запросите письмо ещё раз.',
        )
        return redirect('accounts:resend_email_confirm')

    if user.is_active:
        messages.info(request, 'Email уже подтверждён. Можно войти.')
        return redirect('accounts:login')

    user.is_active = True
    user.save(update_fields=['is_active'])
    request.session.pop('pending_verify_email', None)
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    messages.success(request, 'Email подтверждён. Добро пожаловать!')
    return redirect('accounts:profile')


def resend_email_confirm(request):
    if request.user.is_authenticated:
        return redirect('accounts:profile')

    initial = {}
    pending = request.session.get('pending_verify_email')
    if pending:
        initial['email'] = pending

    if request.method == 'POST':
        form = ResendEmailConfirmForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = (
                User.objects.filter(email__iexact=email, is_active=False)
                .exclude(email='')
                .first()
            )
            if user is not None:
                send_email_confirmation(request, user)
                request.session['pending_verify_email'] = user.email
            messages.success(
                request,
                'Если аккаунт с этим email ожидает подтверждения, мы отправили письмо ещё раз.',
            )
            return redirect('accounts:register_done')
    else:
        form = ResendEmailConfirmForm(initial=initial)
    return render(request, 'accounts/resend_email_confirm.html', {'form': form})


def _get_user_from_uid(uidb64):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        return User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None


@login_required
def profile(request):
    Profile.objects.get_or_create(user=request.user)
    addresses = DeliveryAddress.objects.filter(user=request.user)
    form = ProfileForm(instance=request.user)
    address_form = DeliveryAddressForm()
    edit_address = None

    if request.method == 'GET' and request.GET.get('edit'):
        edit_address = get_object_or_404(
            DeliveryAddress, pk=request.GET.get('edit'), user=request.user
        )
        address_form = DeliveryAddressForm(instance=edit_address)

    if request.method == 'POST':
        action = request.POST.get('action', 'save_profile')
        if action == 'save_profile':
            form = ProfileForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, 'Профиль обновлён')
                return redirect('accounts:profile')
        elif action == 'add_address':
            address_form = DeliveryAddressForm(request.POST)
            if address_form.is_valid():
                addr = address_form.save(commit=False)
                addr.user = request.user
                if not addresses.exists():
                    addr.is_default = True
                addr.save()
                messages.success(request, 'Адрес добавлен')
                return redirect('accounts:profile')
        elif action == 'edit_address':
            edit_address = get_object_or_404(
                DeliveryAddress, pk=request.POST.get('address_id'), user=request.user
            )
            address_form = DeliveryAddressForm(request.POST, instance=edit_address)
            if address_form.is_valid():
                address_form.save()
                messages.success(request, 'Адрес обновлён')
                return redirect('accounts:profile')
        elif action == 'delete_address':
            addr = get_object_or_404(
                DeliveryAddress, pk=request.POST.get('address_id'), user=request.user
            )
            was_default = addr.is_default
            addr.delete()
            if was_default:
                next_addr = DeliveryAddress.objects.filter(user=request.user).first()
                if next_addr:
                    next_addr.is_default = True
                    next_addr.save(update_fields=['is_default'])
            messages.success(request, 'Адрес удалён')
            return redirect('accounts:profile')
        elif action == 'set_default_address':
            addr = get_object_or_404(
                DeliveryAddress, pk=request.POST.get('address_id'), user=request.user
            )
            addr.is_default = True
            addr.save()
            messages.success(request, 'Адрес по умолчанию обновлён')
            return redirect('accounts:profile')

    orders = Order.objects.filter(user=request.user).prefetch_related('items')[:20]
    return render(
        request,
        'accounts/profile.html',
        {
            'form': form,
            'address_form': address_form,
            'edit_address': edit_address,
            'addresses': addresses,
            'orders': orders,
        },
    )
