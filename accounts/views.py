from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render

from cart.models import Order

from .forms import DeliveryAddressForm, LoginForm, ProfileForm, RegisterForm
from .models import DeliveryAddress, Profile


class UserLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    next_page = 'catalog:home'


def register(request):
    if request.user.is_authenticated:
        return redirect('accounts:profile')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно')
            return redirect('accounts:profile')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile(request):
    Profile.objects.get_or_create(user=request.user)
    addresses = DeliveryAddress.objects.filter(user=request.user)
    form = ProfileForm(instance=request.user)
    address_form = DeliveryAddressForm()

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
        elif action == 'delete_address':
            addr = get_object_or_404(DeliveryAddress, pk=request.POST.get('address_id'), user=request.user)
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
            addr = get_object_or_404(DeliveryAddress, pk=request.POST.get('address_id'), user=request.user)
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
            'addresses': addresses,
            'orders': orders,
        },
    )
