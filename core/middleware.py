from django.contrib.auth import logout
from django.http import HttpResponseForbidden

from core.analytics import (
    _register_rate_hit_and_maybe_block,
    _should_rate_limit_request,
    client_ip_for_request,
    is_ip_blocked,
    record_site_visit,
)


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
        ip = client_ip_for_request(request)
        if ip:
            if is_ip_blocked(ip):
                return HttpResponseForbidden('Forbidden')
            if _should_rate_limit_request(request):
                if _register_rate_hit_and_maybe_block(ip):
                    return HttpResponseForbidden('Forbidden')
        return self.get_response(request)


class SiteVisitMiddleware:
    """Считает заходы на витрину с фриз-таймом 5 минут на IP."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        record_site_visit(request)
        return self.get_response(request)
