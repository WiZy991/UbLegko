from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('contacts/', views.contacts, name='contacts'),
    path('set-city/', views.set_city, name='set_city'),
]
