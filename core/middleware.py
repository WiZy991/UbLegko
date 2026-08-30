from django.http import HttpResponseForbidden

from core.analytics import (
    _register_rate_hit_and_maybe_block,
    _should_rate_limit_request,
    client_ip_for_request,
    is_ip_blocked,
    record_site_visit,
)


class IPBlockMiddleware:
    """Блокирует IP, превысившие DDoS-порог (15 запросов за 10 сек → 1 час)."""

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
