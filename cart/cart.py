from decimal import Decimal

from catalog.models import Product

CART_SESSION_KEY = 'cart'


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_KEY)
        if cart is None:
            cart = self.session[CART_SESSION_KEY] = {}
        self.cart = cart

    def add(self, product_id, quantity=1, update=False):
        product_id = str(product_id)
        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0}
        if update:
            self.cart[product_id]['quantity'] = max(1, int(quantity))
        else:
            self.cart[product_id]['quantity'] = max(
                1, self.cart[product_id]['quantity'] + int(quantity)
            )
        self.save()

    def remove(self, product_id):
        product_id = str(product_id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def clear(self):
        self.session[CART_SESSION_KEY] = {}
        self.cart = self.session[CART_SESSION_KEY]
        self.save()

    def save(self):
        self.session.modified = True

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids, is_visible=True)
        product_map = {str(p.id): p for p in products}
        for product_id, item in self.cart.items():
            product = product_map.get(product_id)
            if not product:
                continue
            quantity = item['quantity']
            yield {
                'product': product,
                'quantity': quantity,
                'price': product.price,
                'total': product.price * quantity,
            }

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    @property
    def total_price(self):
        return sum((item['total'] for item in self), Decimal('0'))

    def quantity_of(self, product_id):
        item = self.cart.get(str(product_id))
        return int(item['quantity']) if item else 0

    def quantities_map(self):
        return {int(pid): int(data['quantity']) for pid, data in self.cart.items()}

    def product_ids(self):
        return [int(pid) for pid in self.cart.keys()]
