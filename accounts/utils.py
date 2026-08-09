from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from core.models import SiteSettings

from .tokens import email_confirm_token


def send_email_confirmation(request, user):
    """Отправляет письмо со ссылкой подтверждения регистрации."""
    site = SiteSettings.load()
    protocol = 'https' if request.is_secure() else 'http'
    domain = request.get_host()
    context = {
        'user': user,
        'protocol': protocol,
        'domain': domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': email_confirm_token.make_token(user),
        'site_name': site.brand_name,
    }
    subject = render_to_string('accounts/email/email_confirm_subject.txt', context).strip()
    body = render_to_string('accounts/email/email_confirm_email.txt', context)
    from_email = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER or 'noreply@localhost'
    send_mail(
        subject,
        body,
        from_email,
        [user.email],
        fail_silently=False,
    )
