from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_POST
import logging

from catalog.models import Category, Product
from catalog.recommendations import get_recommendations_for_products
from accounts.models import Profile
from core.context_processors import get_selected_city

from .cart import Cart
from .forms import CheckoutForm
from .models import Favorite, Order, OrderItem

logger = logging.getLogger(__name__)


def _cart_unavailable_response(request, product):
    message = f'«{product.name}» сейчас недоступен для заказа'
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': False, 'error': message}, status=400)
    messages.warning(request, message)
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('catalog:home')
    return redirect(next_url)


def cart_detail(request):
    cart = Cart(request)
    items = list(cart)
    cart_products = [item['product'] for item in items]
    recommendations = get_recommendations_for_products(
        cart_products,
        exclude_ids=cart.product_ids(),
        limit=8,
    )
    favorite_ids = set()
    if request.user.is_authenticated:
        favorite_ids = set(
            Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
        )
    return render(
        request,
        'cart/cart.html',
        {
            'items': items,
            'recommendations': recommendations,
            'categories': Category.objects.filter(is_visible=True),
            'favorite_ids': favorite_ids,
        },
    )


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_visible=True)
    if not product.can_add_to_cart:
        return _cart_unavailable_response(request, product)
    cart = Cart(request)
    quantity = int(request.POST.get('quantity', 1) or 1)
    update = request.POST.get('update') == '1'
    cart.add(product.id, quantity=quantity, update=update)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse(
            {
                'ok': True,
                'cart_count': len(cart),
                'cart_total': f'{cart.total_price:.0f}',
                'message': f'«{product.name}» добавлен в корзину',
            }
        )
    messages.success(request, f'«{product.name}» добавлен в корзину')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('catalog:home')
    return redirect(next_url)


@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    cart.remove(product_id)
    messages.info(request, 'Товар удалён из корзины')
    return redirect('cart:detail')


@require_POST
def cart_update(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_visible=True)
    cart = Cart(request)
    quantity = int(request.POST.get('quantity', 1) or 1)
    if quantity < 1:
        cart.remove(product_id)
        line_total = 0
        removed = True
    else:
        if not product.can_add_to_cart:
            return _cart_unavailable_response(request, product)
        cart.add(product_id, quantity=quantity, update=True)
        removed = False
        line_total = 0
        for item in cart:
            if item['product'].id == int(product_id):
                line_total = item['total']
                quantity = item['quantity']
                break

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse(
            {
                'ok': True,
                'removed': removed,
                'quantity': 0 if removed else quantity,
                'line_total': f'{line_total:.0f}',
                'cart_total': f'{cart.total_price:.0f}',
                'cart_count': len(cart),
                'product_id': int(product_id),
            }
        )
    return redirect('cart:detail')


def checkout(request):
    cart = Cart(request)
    items = list(cart)
    if not items:
        messages.warning(request, 'Корзина пуста')
        return redirect('cart:detail')

    selected_city = get_selected_city(request)
    initial = {}
    if request.user.is_authenticated:
        full_name = (request.user.first_name or '').strip()
        initial['full_name'] = full_name or request.user.username
        initial['email'] = request.user.email or ''
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if profile.phone:
            initial['phone'] = profile.phone
        last_order = (
            Order.objects.filter(user=request.user)
            .order_by('-created_at')
            .first()
        )
        if last_order:
            if not initial.get('phone') and last_order.phone:
                initial['phone'] = last_order.phone
            if last_order.delivery_method:
                initial['delivery_method'] = last_order.delivery_method
            from accounts.models import DeliveryAddress

            if not DeliveryAddress.objects.filter(user=request.user).exists() and last_order.address:
                initial['address'] = last_order.address

    if request.method == 'POST':
        form = CheckoutForm(
            request.POST,
            user=request.user,
            selected_city=selected_city,
        )
        if form.is_valid():
            city = form.cleaned_data['city']
            city_label = CheckoutForm._city_label(city)
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                full_name=form.cleaned_data['full_name'],
                phone=form.cleaned_data['phone'],
                email=form.cleaned_data.get('email', ''),
                delivery_method=form.cleaned_data['delivery_method'],
                address=form.cleaned_data.get('address', ''),
                address_name=form.cleaned_data.get('address_name', ''),
                city=city_label,
                comment=form.cleaned_data['comment'],
            )
            request.session['selected_city_id'] = city.pk
            if request.user.is_authenticated:
                profile, _ = Profile.objects.get_or_create(user=request.user)
                updated = []
                if form.cleaned_data['phone'] and profile.phone != form.cleaned_data['phone']:
                    profile.phone = form.cleaned_data['phone']
                    updated.append('phone')
                email_value = form.cleaned_data.get('email') or ''
                if email_value and request.user.email != email_value:
                    request.user.email = email_value
                    request.user.save(update_fields=['email'])
                name_value = (form.cleaned_data.get('full_name') or '').strip()
                if name_value and request.user.first_name != name_value:
                    request.user.first_name = name_value
                    request.user.save(update_fields=['first_name'])
                if updated:
                    profile.save(update_fields=updated)
            for item in items:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    product_name=item['product'].name,
                    price=item['price'],
                    quantity=item['quantity'],
                )
            email_ok = _send_order_email(order)
            cart.clear()
            if email_ok:
                messages.success(request, f'Заявка №{order.pk} отправлена. Мы свяжемся с вами.')
            else:
                messages.warning(
                    request,
                    f'Заявка №{order.pk} сохранена, но письмо не удалось отправить. '
                    'Мы всё равно обработаем заявку — свяжемся по телефону или email.',
                )
            return redirect('cart:order_success', order_id=order.pk)
    else:
        form = CheckoutForm(
            initial=initial,
            user=request.user,
            selected_city=selected_city,
        )

    return render(
        request,
        'cart/checkout.html',
        {'form': form, 'items': items, 'categories': Category.objects.filter(is_visible=True)},
    )


def order_success(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    return render(request, 'cart/order_success.html', {'order': order})


def _send_order_email(order):
    """Отправляет письмо о заявке. Возвращает True при успехе."""
    from core.models import SiteSettings

    site = SiteSettings.load()
    to_email = site.order_email or settings.ORDER_EMAIL_TO
    subject = f'Заявка №{order.pk} с сайта {site.brand_name}'
    body = render_to_string('cart/email/order.txt', {'order': order, 'site': site})
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
        cc=[order.email] if order.email else None,
    )
    try:
        email.send(fail_silently=False)
        return True
    except Exception:
        logger.exception('Не удалось отправить письмо по заявке №%s на %s', order.pk, to_email)
        return False


@login_required
def favorites(request):
    favs = (
        Favorite.objects.filter(user=request.user)
        .select_related('product', 'product__category')
        .order_by('-created_at')
    )
    products = [f.product for f in favs if f.product.is_visible]
    return render(
        request,
        'cart/favorites.html',
        {
            'products': products,
            'favorite_ids': {p.id for p in products},
            'categories': Category.objects.filter(is_visible=True),
        },
    )


@login_required
@require_POST
def favorite_toggle(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_visible=True)
    fav, created = Favorite.objects.get_or_create(user=request.user, product=product)
    if not created:
        fav.delete()
        active = False
        message = 'Удалено из избранного'
    else:
        active = True
        message = 'Добавлено в избранное'
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        count = Favorite.objects.filter(user=request.user).count()
        return JsonResponse({
            'ok': True,
            'active': active,
            'message': message,
            'favorites_count': count,
        })
    messages.info(request, message)
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('cart:favorites')
    return redirect(next_url)
