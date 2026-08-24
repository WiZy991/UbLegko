from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
import logging

from catalog.models import Category
from cart.models import StainHelpRequest

from .context_processors import SESSION_CITY_KEY
from .forms import StainHelpForm
from .mail import send_shop_email
from .models import City, SiteSettings

logger = logging.getLogger(__name__)


def contacts(request):
    return render(
        request,
        'core/contacts.html',
        {
            'site': SiteSettings.load(),
            'categories': Category.objects.filter(is_visible=True),
        },
    )


def privacy(request):
    return render(
        request,
        'core/privacy.html',
        {
            'site': SiteSettings.load(),
        },
    )


@require_POST
def set_city(request):
    city = get_object_or_404(City, pk=request.POST.get('city_id'), is_active=True)
    request.session[SESSION_CITY_KEY] = city.pk
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'city': city.display_name, 'id': city.pk})
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or '/'
    return redirect(next_url)


@require_POST
def stain_help_submit(request):
    """Принимает обращение «не отмывается»: сохраняет в админку и шлёт на почту."""
    form = StainHelpForm(request.POST)
    if not form.is_valid():
        errors = {
            field: [str(e) for e in errs]
            for field, errs in form.errors.items()
        }
        return JsonResponse({'ok': False, 'errors': errors}, status=400)

    data = form.cleaned_data
    site = SiteSettings.load()

    request_obj = StainHelpRequest.objects.create(
        full_name=data['full_name'],
        phone=data['phone'],
        contact_method=data['contact_method'],
        problem=data['problem'],
        user=request.user if request.user.is_authenticated else None,
        email_sent=False,
    )

    # Тот же канал и получатель, что у заявок с сайта.
    # В теме — имя и телефон: так письма реже теряются в спаме Mail.ru.
    subject = (
        f'Запрос №{request_obj.pk} с сайта {site.brand_name}: '
        f'{data["full_name"]}, {data["phone"]}'
    )
    body = render_to_string(
        'core/email/stain_help.txt',
        {
            'site': site,
            'request_obj': request_obj,
            'full_name': data['full_name'],
            'phone': data['phone'],
            'contact_method': data['contact_method'],
            'problem': data['problem'],
        },
    )
    email_sent = send_shop_email(
        subject=subject,
        body=body,
        log_label=f'Запрос №{request_obj.pk}',
    )
    if email_sent:
        request_obj.email_sent = True
        request_obj.save(update_fields=['email_sent'])
    else:
        logger.error(
            'Запрос №%s сохранён в админке, но письмо на почту не ушло',
            request_obj.pk,
        )

    return JsonResponse({
        'ok': True,
        'request_id': request_obj.pk,
        'message': (
            f'Спасибо! Запрос №{request_obj.pk} принят. '
            'Мы скоро свяжемся с вами.'
        ),
        'email_sent': email_sent,
    })
