from core.analytics import record_site_visit


class SiteVisitMiddleware:
    """Считает уникальные заходы на витрину (один посетитель — один раз в день)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        record_site_visit(request)
        return self.get_response(request)
