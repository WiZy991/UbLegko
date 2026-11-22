from django.contrib.auth import logout
from django.http import HttpResponseForbidden
from django.template.loader import render_to_string

from core.analytics import (
    _is_staff_user,
    _register_rate_hit_and_maybe_block,
    _should_rate_limit_request,
    client_ip_for_request,
    is_ip_blocked,
    record_site_visit,
)

def _blocked_page(ip):
    from core.models import BlockedIP, SiteSettings

    block = BlockedIP.objects.filter(ip_address=ip).only('is_manual').first()
    automatic = not (block and block.is_manual)
    settings_row = SiteSettings.load()
    html = render_to_string('core/ip_blocked.html', {
        'automatic': automatic,
        'tagline': settings_row.tagline,
    })
    return HttpResponseForbidden(html)


class BlockedUserMiddleware:
    """Разлогинивает заблокированных пользователей на любом запросе."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and getattr(user, 'is_authenticated', False):
            from accounts.roles import user_is_blocked

            if user_is_blocked(user):
                logout(request)
        return self.get_response(request)



class IPBlockMiddleware:
    """Блокирует IP, превысившие DDoS-порог (порог задаётся в настройках / статистике)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if _is_staff_user(request):
            return self.get_response(request)
        ip = client_ip_for_request(request)
        if ip:
            if is_ip_blocked(ip):
                return _blocked_page(ip)
            if _should_rate_limit_request(request):
                if _register_rate_hit_and_maybe_block(ip):
                    return _blocked_page(ip)
        return self.get_response(request)


class SiteVisitMiddleware:
    """Считает заходы на витрину с фриз-таймом 5 минут на IP."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        record_site_visit(request)
        return self.get_response(request)
