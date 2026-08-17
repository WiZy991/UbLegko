from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('contacts/', views.contacts, name='contacts'),
    path('privacy/', views.privacy, name='privacy'),
    path('set-city/', views.set_city, name='set_city'),
    path('stain-help/', views.stain_help_submit, name='stain_help'),
]
