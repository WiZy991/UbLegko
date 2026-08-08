from .models import City, SiteSettings

SESSION_CITY_KEY = 'selected_city_id'


def get_selected_city(request):
    city_id = request.session.get(SESSION_CITY_KEY)
    if city_id:
        city = City.objects.filter(pk=city_id, is_active=True).first()
        if city:
            return city
    city = City.objects.filter(is_default=True, is_active=True).first()
    if city:
        return city
    return City.objects.filter(is_active=True).order_by('sort_order', 'name').first()


def site_settings(request):
    try:
        settings_obj = SiteSettings.load()
    except Exception:  # noqa: BLE001
        settings_obj = SiteSettings(
            brand_name='УБИРАЕМСЯЛЕГКО',
            company_name='ООО СОЛНЕЧНЫЙ МЕЧ',
            phone='8-991-496-18-97',
            email='pro-brite_uss@mail.ru',
        )

    try:
        cities = list(City.objects.filter(is_active=True).order_by('name'))
        selected_city = get_selected_city(request)
    except Exception:  # noqa: BLE001
        cities = []
        selected_city = None

    return {
        'site_settings': settings_obj,
        'cities': cities,
        'selected_city': selected_city,
        'selected_city_name': (
            selected_city.display_name if selected_city else settings_obj.city
        ),
    }
