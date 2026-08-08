from django.urls import path

from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.cart_detail, name='detail'),
    path('add/<int:product_id>/', views.cart_add, name='add'),
    path('remove/<int:product_id>/', views.cart_remove, name='remove'),
    path('update/<int:product_id>/', views.cart_update, name='update'),
    path('checkout/', views.checkout, name='checkout'),
    path('success/<int:order_id>/', views.order_success, name='order_success'),
    path('favorites/', views.favorites, name='favorites'),
    path('favorites/toggle/<int:product_id>/', views.favorite_toggle, name='favorite_toggle'),
]
