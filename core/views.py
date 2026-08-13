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
from .models import City, SiteSettings, StainHelpRequest

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


def _send_stain_help_email(*, site, data, to_email: str) -> bool:
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
    # Mail.ru/Beget: From должен совпадать с SMTP-логином, иначе письмо отбрасывается.
    from_email = (
        (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip()
        or (getattr(settings, 'DEFAULT_FROM_EMAIL', '') or '').strip()
    )
    if not from_email:
        logger.error('Нет DEFAULT_FROM_EMAIL / EMAIL_HOST_USER для обращения «не отмывается»')
        return False

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=from_email,
        to=[to_email],
    )
    try:
        if not _is_real_smtp_backend():
            email.send(fail_silently=False)
            logger.error(
                'Обращение «не отмывается»: EMAIL_BACKEND=%s — письмо не ушло на почту',
                settings.EMAIL_BACKEND,
            )
            return False
        sent = email.send(fail_silently=False)
        if not sent:
            logger.error(
                'Обращение «не отмывается»: SMTP вернул 0 (письмо на %s не принято)',
                to_email,
            )
            return False
        logger.info(
            'Обращение «не отмывается» отправлено на %s (от %s, тел. %s)',
            to_email,
            data['full_name'],
            data['phone'],
        )
        return True
    except Exception:
        logger.exception('Не удалось отправить обращение «не отмывается» на %s', to_email)
        return False


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
    to_email = (site.order_email or getattr(settings, 'ORDER_EMAIL_TO', '') or '').strip()

    request_obj = StainHelpRequest.objects.create(
        full_name=data['full_name'],
        phone=data['phone'],
        contact_method=data['contact_method'],
        problem=data['problem'],
        user=request.user if request.user.is_authenticated else None,
        email_sent=False,
    )

    email_sent = False
    if to_email:
        email_sent = _send_stain_help_email(site=site, data=data, to_email=to_email)
        if email_sent:
            request_obj.email_sent = True
            request_obj.save(update_fields=['email_sent'])
    else:
        logger.error('Нет адреса для обращения «не отмывается» (запрос #%s сохранён)', request_obj.pk)

    return JsonResponse({
        'ok': True,
        'message': 'Спасибо! Мы получили обращение и скоро свяжемся.',
        'email_sent': email_sent,
    })
