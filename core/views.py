from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.models import Category

from .context_processors import SESSION_CITY_KEY
from .models import City, SiteSettings


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
