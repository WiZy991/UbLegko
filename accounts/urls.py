from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    path('register/done/', views.register_done, name='register_done'),
    path('confirm-email/<uidb64>/<token>/', views.confirm_email, name='confirm_email'),
    path('resend-email/', views.resend_email_confirm, name='resend_email_confirm'),
    path('profile/', views.profile, name='profile'),
    path('password-reset/', views.UserPasswordResetView.as_view(), name='password_reset'),
    path(
        'password-reset/done/',
        views.UserPasswordResetDoneView.as_view(),
        name='password_reset_done',
    ),
    path(
        'password-reset/<uidb64>/<token>/',
        views.UserPasswordResetConfirmView.as_view(),
        name='password_reset_confirm',
    ),
]
