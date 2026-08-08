from .cart import Cart


def cart(request):
    from cart.models import Favorite

    c = Cart(request)
    favorites_count = 0
    if getattr(request, 'user', None) is not None and request.user.is_authenticated:
        favorites_count = Favorite.objects.filter(user=request.user).count()
    return {
        'cart': c,
        'cart_total': c.total_price,
        'cart_count': len(c),
        'favorites_count': favorites_count,
    }
