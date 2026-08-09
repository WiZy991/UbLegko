from django.contrib import admin

from .models import Favorite, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'price', 'quantity')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'full_name',
        'phone',
        'delivery_method',
        'email',
        'address',
        'status',
        'created_at',
        'total_display',
    )
    list_filter = ('status', 'delivery_method', 'created_at')
    search_fields = ('full_name', 'phone', 'email', 'address')
    list_editable = ('status',)
    readonly_fields = (
        'user',
        'full_name',
        'phone',
        'email',
        'delivery_method',
        'address',
        'comment',
        'created_at',
    )
    inlines = [OrderItemInline]

    @admin.display(description='Сумма')
    def total_display(self, obj):
        return f'{obj.total:.0f} руб'


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    search_fields = ('user__username', 'product__name')
