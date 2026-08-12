from django.conf import settings
from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
import logging

from catalog.models import Category

from .context_processors import SESSION_CITY_KEY
from .forms import StainHelpForm
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


@require_POST
def set_city(request):
    city = get_object_or_404(City, pk=request.POST.get('city_id'), is_active=True)
    request.session[SESSION_CITY_KEY] = city.pk
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'city': city.display_name, 'id': city.pk})
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or '/'
    return redirect(next_url)


def _is_real_smtp_backend():
    backend = (settings.EMAIL_BACKEND or '').lower()
    return (
        'smtp' in backend
        and 'console' not in backend
        and 'dummy' not in backend
        and 'locmem' not in backend
    )


@require_POST
def stain_help_submit(request):
    """Принимает обращение «не отмывается» и отправляет на почту магазина."""
    form = StainHelpForm(request.POST)
    if not form.is_valid():
        errors = {
            field: [str(e) for e in errs]
            for field, errs in form.errors.items()
        }
        return JsonResponse({'ok': False, 'errors': errors}, status=400)

    site = SiteSettings.load()
    to_email = (site.order_email or getattr(settings, 'ORDER_EMAIL_TO', '') or '').strip()
    if not to_email:
        logger.error('Нет адреса для обращения «не отмывается»')
        return JsonResponse(
            {'ok': False, 'error': 'Сейчас нельзя отправить обращение. Позвоните нам.'},
            status=503,
        )

    data = form.cleaned_data
    subject = f'Обращение: не отмывается — {site.brand_name}'
    body = render_to_string(
        'core/email/stain_help.txt',
        {
            'site': site,
            'full_name': data['full_name'],
            'phone': data['phone'],
            'contact_method': data['contact_method'],
            'problem': data['problem'],
        },
    )
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
        to=[to_email],
        reply_to=None,
    )
    try:
        if not _is_real_smtp_backend():
            email.send(fail_silently=False)
            logger.error(
                'Обращение «не отмывается»: EMAIL_BACKEND=%s — письмо не ушло на почту',
                settings.EMAIL_BACKEND,
            )
            return JsonResponse(
                {
                    'ok': False,
                    'error': 'Письмо не отправлено (почта не настроена). Позвоните нам.',
                },
                status=503,
            )
        sent = email.send(fail_silently=False)
        if not sent:
            return JsonResponse(
                {'ok': False, 'error': 'Не удалось отправить. Попробуйте позже или позвоните.'},
                status=502,
            )
    except Exception:
        logger.exception('Не удалось отправить обращение «не отмывается» на %s', to_email)
        return JsonResponse(
            {'ok': False, 'error': 'Не удалось отправить. Попробуйте позже или позвоните.'},
            status=500,
        )

    return JsonResponse({
        'ok': True,
        'message': 'Спасибо! Мы получили обращение и скоро свяжемся.',
    })
